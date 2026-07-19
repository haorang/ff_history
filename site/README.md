# League Almanac — website

React + Vite frontend for the archived NFL.com fantasy league history
(2018–2025), pulled from the saved HTML in `../raw/`.

## Run it

```bash
cd site
npm install      # first time only
npm run dev      # → http://localhost:5173
```

## Where the data comes from

The app reads JSON from `public/data/` — `index.json` plus one file per season
(e.g. `2018.json`). Those are generated from the captured HTML by the parser:

```bash
cd ..                       # ff_history root
source .venv/bin/activate
python build_data.py        # writes site/public/data/*.json
```

Re-run `build_data.py` any time the crawl captures more seasons, then refresh
the browser. Nothing else to wire up.

## Rename the league

Edit `LEAGUE_NAME` and `LEAGUE_TAGLINE` at the top of `src/lib.js`.

## Project structure

```
src/
  lib.js          data loading (fetch + cache), formatting helpers, league name
  App.jsx         layout — sticky top bar + season nav
  pages/
    Home.jsx      hero · champions roll · all-time standings · record book
    Season.jsx    tabs: Standings · Scores (+ expandable box scores) · Draft · Transactions
  styles.css      design system — dark "night broadcast" theme; tokens at the top
```

Data shapes: see the objects written in `../build_data.py` (`build_season`,
`build_alltime`, `build_records`).

## Extending (a few starting points)

- **New tab / view** → add a component in `Season.jsx` and a name to `TABS`.
- **New page/route** → add a `<Route>` in `src/main.jsx`.
- **New all-time stat or record** → compute it in `build_alltime()` /
  `build_records()` in `../build_data.py`, then read it from `index.json`.
- **Charts** → `npm i recharts` (data's already in the JSON — e.g. a team's
  weekly scoring line, or points-for over seasons).
- **Full box-score stats** → the granular per-category stats are captured in
  `../raw/<season>/gamecenter_*_full.html`; add a parser branch to include them.
- **Head-to-head / rivalries** → all matchups are in each season's `weeks`; a
  cross-season H2H matrix is a natural next feature.

## Build to share

```bash
npm run build    # → dist/  (static files, host anywhere)
npm run preview  # preview that build locally
```
