"""Shared config for the NFL.com fantasy league history capture."""
from pathlib import Path

LEAGUE_ID = "6236348"
# 2016 & 2017 have no data on NFL.com for this league (league started 2018).
SEASONS = list(range(2018, 2026))  # 2018..2025 inclusive

# Roster size per season (2019 & 2020 were 10-team years); used to avoid
# crawling nonexistent teamIds. Defaults to 12 for any season not listed.
TEAM_COUNT = {2019: 10, 2020: 10}

BASE = f"https://fantasy.nfl.com/league/{LEAGUE_ID}/history"

ROOT = Path(__file__).resolve().parent
AUTH_FILE = ROOT / "auth.json"
RAW_DIR = ROOT / "raw"          # saved page HTML
SHOTS_DIR = ROOT / "shots"      # full-page screenshots
NET_DIR = ROOT / "net"          # captured JSON network responses
MANIFEST = ROOT / "manifest.csv"

# A logged-in league-history page always shows this sub-nav link; a login /
# redirect page never does. Used both to confirm auth and to validate captures.
LOGGED_IN_MARKER = "Draft Results"
