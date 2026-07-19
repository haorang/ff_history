"""Parsers that turn captured NFL.com history HTML into clean structured data.
Phase 2. Each function takes raw HTML and returns plain dicts/lists.
"""
import re
from bs4 import BeautifulSoup


def _soup(html):
    return BeautifulSoup(html, "lxml")


def _f(x):
    try:
        return float(str(x).replace(",", ""))
    except Exception:
        return None


def _split_player(s):
    """'M. Ryan QB - ATL' -> ('M. Ryan', 'ATL'); 'Broncos DEF' -> ('Broncos','')."""
    m = re.match(r"^(.*?)\s+[A-Z/]+\s+-\s+([A-Z]+)$", s)
    if m:
        return m.group(1), m.group(2)
    m2 = re.match(r"^(.*?)\s+DEF$", s)
    if m2:
        return m2.group(1), ""
    return s, ""


def _players(table):
    """Extract player rows from a game-center player table."""
    out = []
    if not table:
        return out
    for tr in table.select("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all("td")]
        if len(cells) < 6 or not cells[0]:
            continue
        pts = _f(cells[-1])          # points are always the last column
        if pts is None:              # skips header / non-player rows
            continue
        name, nfl = _split_player(cells[1])
        out.append({"pos": cells[0], "name": name, "nfl": nfl,
                    "opp": cells[2], "result": cells[3], "pts": pts})
    return out


# --------------------------------------------------------------------------- #
# Standings
# --------------------------------------------------------------------------- #
def parse_standings_regular(html):
    """Regular-season standings table -> list of team rows."""
    s = _soup(html)
    table = s.select_one("table")
    out = []
    if not table:
        return out
    for tr in table.select("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) != 7:
            continue
        m = re.match(r"^(\d+)", cells[0])  # cells[0] may be "5 + 1" (rank movement)
        if not m:
            continue
        _, team, rec, pct, stk, pf, pa = cells
        out.append({"rank": int(m.group(1)), "team": team, "record": rec,
                    "pct": pct, "streak": stk, "pf": _f(pf), "pa": _f(pa)})
    return out


def parse_final_standings(html):
    """Final placement (playoff finish) -> ordered [{place, team}]."""
    s = _soup(html)
    out = []
    for p in s.select(".place"):
        row = p.parent
        link = row.select_one("a") if row else None
        team = link.get_text(strip=True) if link else None
        m = re.match(r"(\d+)", p.get_text(strip=True))
        if m and team:
            out.append({"place": int(m.group(1)), "team": team})
    return out


# --------------------------------------------------------------------------- #
# Schedule + box scores
# --------------------------------------------------------------------------- #
def parse_schedule_week(html):
    """One week's matchups -> list of {team_a, pts_a, team_b, pts_b}."""
    s = _soup(html)
    names = [n.get_text(strip=True) for n in s.select(".teamName")]
    totals = [t.get_text(strip=True) for t in s.select(".teamTotal")]
    out = []
    for i in range(0, min(len(names), len(totals)) - 1, 2):
        out.append({"team_a": names[i], "pts_a": _f(totals[i]),
                    "team_b": names[i + 1], "pts_b": _f(totals[i + 1])})
    return out


def parse_boxscore(html):
    """Game-center simple box score -> both teams with starters + bench.

    The page has a scoreboard strip listing every matchup, so we scope strictly
    to this matchup's two columns: the .teamWrap-N that actually hold player
    tables ([0]=starters, [1]=bench).
    """
    s = _soup(html)
    names = [e.get_text(strip=True) for e in s.select(".matchup .teamName")]
    main_wraps = [w for w in s.select("[class*='teamWrap-']")
                  if w.select_one("table.tableType-player")][:2]
    teams = []
    for i, wrap in enumerate(main_wraps):
        tbls = wrap.select("table.tableType-player")
        starters = _players(tbls[0]) if tbls else []
        bench = _players(tbls[1]) if len(tbls) > 1 else []
        teams.append({
            "team": names[i] if i < len(names) else f"team{i + 1}",
            "total": round(sum(p["pts"] or 0 for p in starters), 2),
            "starters": starters, "bench": bench,
        })
    return teams


# --------------------------------------------------------------------------- #
# Draft
# --------------------------------------------------------------------------- #
def parse_draft_round(html):
    """One draft round -> list of {pick, player, pos_team, team, manager}."""
    s = _soup(html)
    result = s.select_one("[class*='result']")
    text = result.get_text("\n", strip=True) if result else ""
    picks = []
    for m in re.finditer(
            r"(\d+)\.\s+(.+?)\s+([A-Z/]+(?: - [A-Z]+)?)\s+To\s+(.+?)(?=\n\d+\.|\Z)",
            text, re.S):
        drafted = " ".join(m.group(4).split())
        parts = drafted.split(" ")
        manager = parts[-1] if len(parts) > 1 else ""
        team = " ".join(parts[:-1]) if len(parts) > 1 else drafted
        picks.append({"pick": int(m.group(1)), "player": m.group(2).strip(),
                      "pos_team": m.group(3).strip(), "team": team[:40],
                      "manager": manager})
    return picks


# --------------------------------------------------------------------------- #
# Managers + transactions
# --------------------------------------------------------------------------- #
def parse_owners(html):
    """Managers/owners table -> {team: {manager, co_manager, moves, trades}}."""
    s = _soup(html)
    t = s.select_one("table")
    out = {}
    if not t:
        return out
    for tr in t.select("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all("td")]
        if len(cells) >= 2 and cells[0] and cells[0] != "Team":
            out[cells[0]] = {
                "manager": cells[1],
                "co_manager": cells[2] if len(cells) > 2 else "",
                "moves": cells[4] if len(cells) > 4 else "",
                "trades": cells[5] if len(cells) > 5 else "",
            }
    return out


def parse_transactions(html):
    """One transactions page -> list of transaction rows."""
    s = _soup(html)
    out = []
    for tr in s.select("table tbody tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all("td")]
        if len(cells) >= 7 and cells[0]:
            out.append({"date": cells[0], "week": cells[1], "type": cells[2],
                        "player": cells[3], "from": cells[4], "to": cells[5],
                        "by": cells[6].split(" via ")[0]})
    return out
