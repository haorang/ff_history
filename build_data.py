"""Aggregate captured HTML -> clean JSON for the website.

Reads raw/<season>/*.html, runs the parsers, writes:
  site/data/<season>.json   full detail for one season
  site/data/index.json      season list, champions, all-time manager table

Re-runnable: just run again after the crawl captures more seasons.
Usage:  python build_data.py
"""
import json
import glob
import re
from pathlib import Path

import parse
from config import LEAGUE_ID, ROOT

RAW = ROOT / "raw"
OUT = ROOT / "site" / "public" / "data"


def _read(p):
    f = RAW / p
    if f.exists() and f.stat().st_size > 1500:
        return f.read_text(encoding="utf-8")
    return None


def _wl(record):
    """'10-3-0' -> (10,3,0)."""
    m = re.match(r"(\d+)-(\d+)-(\d+)", record or "")
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def build_season(season):
    sdir = str(season)
    data = {"season": season, "league_id": LEAGUE_ID}

    # managers (team -> manager info)
    owners_html = _read(f"{sdir}/owners.html")
    managers = parse.parse_owners(owners_html) if owners_html else {}
    data["managers"] = managers

    def mgr(team):
        return managers.get(team, {}).get("manager", "")

    # standings
    sr = _read(f"{sdir}/standings_regular.html")
    standings = parse.parse_standings_regular(sr) if sr else []
    for r in standings:
        r["manager"] = mgr(r["team"])
    data["standings"] = standings
    data["num_teams"] = len(standings)

    # final placement
    sf = _read(f"{sdir}/standings_final.html")
    final = parse.parse_final_standings(sf) if sf else []
    for r in final:
        r["manager"] = mgr(r["team"])
    data["final"] = final
    if final:
        podium = {1: "champion", 2: "runner_up", 3: "third"}
        for r in final:
            if r["place"] in podium:
                data[podium[r["place"]]] = {"team": r["team"], "manager": r["manager"]}

    # regular-season length from the top team's record (W+L+T)
    reg_weeks = sum(_wl(standings[0]["record"])) if standings else 13
    data["reg_weeks"] = reg_weeks

    # weekly matchups
    weeks = {}
    for w in range(1, 18):
        html = _read(f"{sdir}/schedule_week{w:02d}.html")
        if not html:
            continue
        mus = parse.parse_schedule_week(html)
        if not mus:
            continue
        for m in mus:
            m["mgr_a"], m["mgr_b"] = mgr(m["team_a"]), mgr(m["team_b"])
            if m["pts_a"] is not None and m["pts_b"] is not None:
                m["winner"] = m["team_a"] if m["pts_a"] >= m["pts_b"] else m["team_b"]
        weeks[str(w)] = {"playoff": w > reg_weeks, "matchups": mus}
    data["weeks"] = weeks

    # box scores: week -> team -> lineup (from simple game-center pages)
    box = {}
    for f in sorted(glob.glob(str(RAW / sdir / "gamecenter_team*_week*.html"))):
        if f.endswith("_full.html"):
            continue
        m = re.search(r"week(\d+)\.html$", f)
        if not m:
            continue
        wk = str(int(m.group(1)))
        html = Path(f).read_text(encoding="utf-8")
        if len(html) < 2000:
            continue
        for t in parse.parse_boxscore(html):
            if not t["starters"]:
                continue
            box.setdefault(wk, {})[t["team"]] = {
                "total": t["total"], "starters": t["starters"], "bench": t["bench"],
            }
    data["boxscores"] = box

    # draft
    draft = []
    for r in range(1, 17):
        html = _read(f"{sdir}/draft_round{r:02d}.html")
        if not html:
            continue
        picks = parse.parse_draft_round(html)
        n = data["num_teams"] or len(picks)
        for p in picks:
            p["round"] = r
            p["overall"] = (r - 1) * n + p["pick"]
            draft.append(p)
    data["draft"] = draft

    # transactions (all offset pages concatenated)
    txns = []
    for f in sorted(glob.glob(str(RAW / sdir / "transactions_offset*.html"))):
        txns.extend(parse.parse_transactions(Path(f).read_text(encoding="utf-8")))
    # de-dupe (pages can overlap) while preserving order
    seen, uniq = set(), []
    for t in txns:
        key = (t["date"], t["type"], t["player"], t["from"], t["to"])
        if key not in seen:
            seen.add(key)
            uniq.append(t)
    data["transactions"] = uniq

    return data


# Seasons that predate the NFL.com archive (2016–17): no box scores / records
# survive, only these placements the league remembers. Keyed by season -> {place: manager}.
MANUAL_FINISHES = {
    2017: {1: "Alan", 2: "Haoran", 3: "Leo"},
    2016: {1: "Griffin", 2: "Leo", 3: "Haoran", 9: "Vincent", 10: "Sajan"},
}

def build_alltime(seasons_data):
    """Career table keyed by manager, joined across seasons."""
    career = {}
    for d in seasons_data:
        champ = d.get("champion", {}).get("manager")
        final_place = {r["team"]: r["place"] for r in d.get("final", [])}
        for r in d["standings"]:
            m = r["manager"] or r["team"]
            c = career.setdefault(m, {"manager": m, "seasons": 0, "titles": 0,
                                      "w": 0, "l": 0, "t": 0, "pf": 0.0, "pa": 0.0,
                                      "best_finish": 99, "finishes": [], "team_names": set()})
            w, l, t = _wl(r["record"])
            c["seasons"] += 1
            c["w"] += w
            c["l"] += l
            c["t"] += t
            c["pf"] += r["pf"] or 0
            c["pa"] += r["pa"] or 0
            c["team_names"].add(r["team"])
            place = final_place.get(r["team"], 99)
            if place != 99:
                c["best_finish"] = min(c["best_finish"], place)
                c["finishes"].append(place)
        if champ:
            career.setdefault(champ, {"manager": champ, "seasons": 0, "titles": 0,
                                      "w": 0, "l": 0, "t": 0, "pf": 0.0, "pa": 0.0,
                                      "best_finish": 99, "finishes": [], "team_names": set()})
            career[champ]["titles"] += 1

    # fold in remembered pre-archive finishes (2016–17)
    for places in MANUAL_FINISHES.values():
        for place, m in places.items():
            c = career.get(m)
            if c is None:
                c = career[m] = {"manager": m, "seasons": 0, "titles": 0, "w": 0,
                                 "l": 0, "t": 0, "pf": 0.0, "pa": 0.0,
                                 "best_finish": 99, "finishes": [], "team_names": set()}
            c["seasons"] += 1
            c["best_finish"] = min(c["best_finish"], place)
            c["finishes"].append(place)
            if place == 1:
                c["titles"] += 1

    out = []
    for c in career.values():
        c["team_names"] = sorted(c["team_names"])
        c["pf"] = round(c["pf"], 2)
        c["pa"] = round(c["pa"], 2)
        games = c["w"] + c["l"] + c["t"]
        c["win_pct"] = round(c["w"] / games, 3) if games else 0
        fins = c.pop("finishes")
        c["avg_finish"] = round(sum(fins) / len(fins), 1) if fins else None
        if c["best_finish"] == 99:
            c["best_finish"] = None
        out.append(c)
    out.sort(key=lambda x: (-x["titles"], -x["win_pct"], -x["pf"]))
    return out


def build_records(seasons_data):
    """Fun all-time league records computed across every matchup."""
    games = []   # one entry per team-performance in a matchup
    blowouts = []
    for d in seasons_data:
        for wk, wd in d["weeks"].items():
            for m in wd["matchups"]:
                a, b = m.get("pts_a"), m.get("pts_b")
                if a is None or b is None:
                    continue
                games.append({"season": d["season"], "week": int(wk),
                              "team": m["team_a"], "manager": m.get("mgr_a", ""),
                              "pts": a, "opp": m["team_b"], "opp_pts": b,
                              "playoff": wd["playoff"]})
                games.append({"season": d["season"], "week": int(wk),
                              "team": m["team_b"], "manager": m.get("mgr_b", ""),
                              "pts": b, "opp": m["team_a"], "opp_pts": a,
                              "playoff": wd["playoff"]})
                hi, lo = (m["team_a"], m["team_b"]) if a >= b else (m["team_b"], m["team_a"])
                blowouts.append({"season": d["season"], "week": int(wk),
                                 "winner": hi, "loser": lo,
                                 "margin": round(abs(a - b), 2),
                                 "hi": max(a, b), "lo": min(a, b)})
    season_pf = [{"season": d["season"], "team": r["team"], "manager": r["manager"],
                  "pf": r["pf"]} for d in seasons_data for r in d["standings"]]
    top = lambda lst, key, n=5: sorted(lst, key=key, reverse=True)[:n]
    return {
        "highest_games": top(games, lambda g: g["pts"]),
        "lowest_games": sorted([g for g in games], key=lambda g: g["pts"])[:5],
        "biggest_blowouts": top(blowouts, lambda b: b["margin"]),
        "closest_games": sorted(blowouts, key=lambda b: b["margin"])[:5],
        "top_season_pf": top(season_pf, lambda s: s["pf"]),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    seasons = sorted(int(p.name) for p in RAW.iterdir()
                     if p.is_dir() and p.name.isdigit())
    seasons_data = []
    for s in seasons:
        d = build_season(s)
        if not d["standings"]:
            print(f"  {s}: no standings yet, skipping")
            continue
        (OUT / f"{s}.json").write_text(json.dumps(d), encoding="utf-8")
        bs = sum(len(v) for v in d["boxscores"].values())
        print(f"  {s}: {d['num_teams']} teams, {len(d['weeks'])} weeks, "
              f"{bs} box scores, {len(d['draft'])} picks, "
              f"{len(d['transactions'])} txns, champ={d.get('champion',{}).get('team','?')}")
        seasons_data.append(d)

    champions = {d["season"]: d.get("champion", {}) for d in seasons_data}
    for yr, places in MANUAL_FINISHES.items():
        if 1 in places:
            champions[yr] = {"team": "", "manager": places[1]}
    index = {
        "league_id": LEAGUE_ID,
        "seasons": [d["season"] for d in seasons_data],
        "champions": champions,
        "champion_years": sorted(champions.keys()),
        "alltime": build_alltime(seasons_data),
        "records": build_records(seasons_data),
    }
    (OUT / "index.json").write_text(json.dumps(index), encoding="utf-8")
    total = sum((OUT / f"{d['season']}.json").stat().st_size for d in seasons_data)
    print(f"\nWrote {len(seasons_data)} seasons + index to {OUT}")
    print(f"Total season JSON: {total/1024:.0f} KB")


if __name__ == "__main__":
    main()
