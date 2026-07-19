"""Capture NFL.com fantasy league-history pages to disk as raw HTML (+ optional
screenshot + captured JSON network responses), organized by season.

Phase 1 = pure capture. We save everything raw and never throw it away; parsing
into clean CSV/JSON happens later, offline, from these files.

Usage:
  python crawl.py --test                 # small 2018-only smoke test
  python crawl.py                        # full crawl, all seasons (resumable)
  python crawl.py --seasons 2018 2019    # subset of seasons
  python crawl.py --no-shots             # skip screenshots (faster/smaller)
"""
import argparse
import asyncio
import csv
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from config import (
    LEAGUE_ID, SEASONS, TEAM_COUNT, BASE, AUTH_FILE, RAW_DIR, SHOTS_DIR, NET_DIR,
    MANIFEST, LOGGED_IN_MARKER,
)

WEEKS = list(range(1, 18))      # capture weeks 1..17 (empties detected & skipped)
ROUNDS = list(range(1, 17))     # draft rounds 1..16 (empties detected & skipped)
MAX_TXN_OFFSET = 3000           # safety cap for transaction pagination
REQUEST_DELAY = 0.8             # polite delay between page loads (seconds)


def season_jobs(season: int):
    """Yield (url, name) capture jobs for one season. `name` is the file stem
    under raw/<season>/. Transactions & empties are handled dynamically in run().
    """
    s = season
    b = f"{BASE}/{s}"
    yield (f"{b}/standings?historyStandingsType=final", "standings_final")
    yield (f"{b}/standings?historyStandingsType=regular", "standings_regular")
    yield (f"{b}/owners", "owners")
    yield (f"{b}/playoffs?bracketType=championship&standingsTab=playoffs", "playoffs_championship")
    yield (f"{b}/playoffs?bracketType=consolation&standingsTab=playoffs", "playoffs_consolation")
    for w in WEEKS:
        yield (f"{b}/schedule?gameSeason={s}&leagueId={LEAGUE_ID}"
               f"&scheduleDetail={w}&scheduleType=week&standingsTab=schedule",
               f"schedule_week{w:02d}")
    for t in range(1, TEAM_COUNT.get(season, 12) + 1):
        for w in WEEKS:
            # default view = simple box score (team totals + summary)
            yield (f"{b}/teamgamecenter?teamId={t}&week={w}",
                   f"gamecenter_team{t:02d}_week{w:02d}")
            # full box score = complete granular per-player stats
            yield (f"{b}/teamgamecenter?gameCenterTab=track&teamId={t}"
                   f"&trackType=fbs&week={w}",
                   f"gamecenter_team{t:02d}_week{w:02d}_full")
    for r in ROUNDS:
        yield (f"{b}/draftresults?draftResultsDetail={r}"
               f"&draftResultsTab=round&draftResultsType=results",
               f"draft_round{r:02d}")


def looks_valid(html: str) -> bool:
    """A real league-history page renders the sub-nav (Draft Results); game-center
    pages use a different nav but render player tables (tableType-player)."""
    return (LOGGED_IN_MARKER in html
            or "tableType-player" in html
            or "Total Points" in html)


async def capture(page, url, out_html: Path, shot: Path | None, net_path: Path | None,
                  wait_selector: str | None = None):
    """Load one URL; save HTML, optional screenshot, optional captured JSON.
    Returns (ok, bytes, valid)."""
    captured = []

    def on_response(resp):
        try:
            ct = resp.headers.get("content-type", "")
            if "json" in ct and "nfl.com" in resp.url:
                captured.append(resp)
        except Exception:
            pass

    page.on("response", on_response)
    try:
        await page.goto(url, wait_until="load", timeout=45000)
        if wait_selector:
            # A valid game-center page ships a large HTML shell at load (~500KB)
            # even before its async player table renders; a nonexistent
            # team/season returns a ~39-byte empty body. Skip the wait for those.
            early = await page.content()
            if len(early) < 2000:
                html = early
            else:
                try:
                    await page.wait_for_selector(wait_selector, timeout=7000)
                except Exception:
                    pass
                await asyncio.sleep(0.4)
                html = await page.content()
        else:
            await asyncio.sleep(0.4)  # let any late XHR settle
            html = await page.content()
        out_html.parent.mkdir(parents=True, exist_ok=True)
        out_html.write_text(html, encoding="utf-8")

        if shot is not None:
            shot.parent.mkdir(parents=True, exist_ok=True)
            try:
                await page.screenshot(path=str(shot), full_page=True)
            except Exception:
                pass

        if net_path is not None and captured:
            payloads = []
            for r in captured:
                try:
                    payloads.append({"url": r.url, "body": await r.text()})
                except Exception:
                    pass
            if payloads:
                net_path.parent.mkdir(parents=True, exist_ok=True)
                net_path.write_text(json.dumps(payloads, indent=2), encoding="utf-8")

        return True, len(html), looks_valid(html)
    except Exception as e:
        print(f"    ! error {url}: {e}")
        return False, 0, False
    finally:
        page.remove_listener("response", on_response)


def txn_row_count(html: str) -> int:
    """Count transaction rows on a transactions page (to detect the last page)."""
    soup = BeautifulSoup(html, "lxml")
    # Transaction rows live in the history transactions table body.
    rows = soup.select("table tbody tr")
    # Fall back: count rows that carry a player/date cell.
    return len([r for r in rows if r.find("td")])


async def run(seasons, want_shots, test):
    RAW_DIR.mkdir(exist_ok=True)
    manifest_rows = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx_kwargs = {}
        if AUTH_FILE.exists():
            ctx_kwargs["storage_state"] = str(AUTH_FILE)
        context = await browser.new_context(**ctx_kwargs)
        page = await context.new_page()

        for season in seasons:
            print(f"\n=== SEASON {season} ===")
            jobs = list(season_jobs(season))
            if test:
                # one of each core type only
                keep = {"standings_final", "standings_regular", "owners",
                        "playoffs_championship", "schedule_week01",
                        "gamecenter_team01_week04", "draft_round01"}
                jobs = [j for j in jobs if j[1] in keep]

            for url, name in jobs:
                out_html = RAW_DIR / str(season) / f"{name}.html"
                if out_html.exists() and out_html.stat().st_size > 2000 and not test:
                    continue  # resumable: already captured
                shot = (SHOTS_DIR / str(season) / f"{name}.png") if want_shots else None
                net_path = NET_DIR / str(season) / f"{name}.json"
                wait_sel = "table.tableType-player" if name.startswith("gamecenter") else None
                ok, nbytes, valid = await capture(page, url, out_html, shot, net_path, wait_sel)
                flag = "ok " if valid else ("EMPTY" if ok else "FAIL")
                print(f"  [{flag}] {name} ({nbytes} bytes)")
                manifest_rows.append([season, name, url, ok, valid, nbytes])
                await asyncio.sleep(REQUEST_DELAY)

            # --- transactions: paginate until an empty page ---
            if not test:
                offset = 0
                while offset <= MAX_TXN_OFFSET:
                    name = f"transactions_offset{offset:04d}"
                    out_html = RAW_DIR / str(season) / f"{name}.html"
                    url = f"{BASE}/{season}/transactions" + (f"?offset={offset}" if offset else "")
                    if out_html.exists() and out_html.stat().st_size > 2000:
                        rows = txn_row_count(out_html.read_text(encoding="utf-8"))
                    else:
                        shot = (SHOTS_DIR / str(season) / f"{name}.png") if want_shots else None
                        net_path = NET_DIR / str(season) / f"{name}.json"
                        ok, nbytes, valid = await capture(page, url, out_html, shot, net_path)
                        rows = txn_row_count(out_html.read_text(encoding="utf-8")) if ok else 0
                        print(f"  [txn ] {name}: {rows} rows")
                        manifest_rows.append([season, name, url, ok, valid, nbytes])
                        await asyncio.sleep(REQUEST_DELAY)
                    if rows == 0:
                        break
                    offset += 21

        await browser.close()

    write_header = not MANIFEST.exists()
    with open(MANIFEST, "a", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["season", "name", "url", "ok", "valid", "bytes"])
        w.writerows(manifest_rows)
    print(f"\nManifest updated: {MANIFEST}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="small 2018-only smoke test")
    ap.add_argument("--seasons", nargs="+", type=int, default=None)
    ap.add_argument("--no-shots", action="store_true", help="skip screenshots")
    args = ap.parse_args()

    seasons = args.seasons or ([2018] if args.test else SEASONS)
    asyncio.run(run(seasons, want_shots=not args.no_shots, test=args.test))


if __name__ == "__main__":
    main()
