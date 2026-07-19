import { Link } from 'react-router-dom'
import { useAsync, loadIndex, fmt, ord, LEAGUE_NAME } from '../lib'

function Loading() {
  return <div className="loading"><div className="spinner" />Loading the almanac…</div>
}

export default function Home() {
  const { data, loading, error } = useAsync(loadIndex, [])
  if (loading) return <Loading />
  if (error) return <div className="errbox">Couldn’t load data. Run <code>python build_data.py</code> and start the dev server.</div>

  const { seasons, champions, alltime, records } = data
  const championYears = data.champion_years || seasons
  const latest = seasons[seasons.length - 1]
  const reigning = champions[latest] || {}

  return (
    <>
      {/* hero */}
      <section className="hero">
        <div className="hero-sun" />
        <div className="hero-inner">
          <div>
            <span className="eyebrow">{seasons[0]} – {seasons[seasons.length - 1]} · League ID {data.league_id}</span>
            <h1 className="hero-title">{LEAGUE_NAME.split(' ')[0]}<br />{LEAGUE_NAME.split(' ').slice(1).join(' ') || 'Almanac'}</h1>
            <div className="hero-sub">
              <div className="hero-stat"><b>{seasons.length}</b><span>Seasons</span></div>
              <div className="hero-stat"><b>{alltime.length}</b><span>Managers</span></div>
              <div className="hero-stat"><b>{new Set(Object.values(champions).map(c => c.manager)).size}</b><span>Champions</span></div>
            </div>
          </div>
          <div className="reign">
            <div className="lbl">🏆 Reigning Champion ’{String(latest).slice(2)}</div>
            <Link to={`/season/${latest}`} className="champ"><div className="champ">{reigning.team || '—'}</div></Link>
            <div className="mgr">{reigning.manager}</div>
          </div>
        </div>
      </section>

      {/* champions */}
      <div className="section-head">
        <div><span className="eyebrow">Roll of Honor</span><h2 className="section-title">Champions</h2></div>
      </div>
      <div className="champ-rail">
        {championYears.map((s) => {
          const c = champions[s] || {}
          const big = c.team || c.manager || '—'
          const small = c.manager && c.manager !== big ? c.manager : ''
          const playable = seasons.includes(s)
          const inner = (
            <>
              <span className="cup">🏆</span>
              <div className="yr">{s}</div>
              <div className="team">{big}</div>
              <div className="who">{small || (playable ? ' ' : 'pre-archive')}</div>
            </>
          )
          return playable
            ? <Link key={s} to={`/season/${s}`} className="champ-card">{inner}</Link>
            : <div key={s} className="champ-card no-link">{inner}</div>
        })}
      </div>

      {/* all-time */}
      <div className="section-head">
        <div><span className="eyebrow">Every manager, all seasons</span><h2 className="section-title">All-Time Standings</h2></div>
      </div>
      <div className="table-wrap">
        <table className="grid">
          <thead>
            <tr>
              <th className="l">Manager</th><th>Titles</th><th>Szns</th>
              <th>W</th><th>L</th><th>T</th><th>Win %</th><th>Points For</th><th>Best</th><th>Avg Fin</th>
            </tr>
          </thead>
          <tbody>
            {alltime.map((m) => (
              <tr key={m.manager}>
                <td className="l teamcell">{m.manager}
                  {m.team_names?.length ? <small>{m.team_names.slice(0, 2).join(' · ')}{m.team_names.length > 2 ? ' …' : ''}</small> : null}
                </td>
                <td className="mono">{m.titles ? '🏆'.repeat(m.titles) : <span className="faint">—</span>}</td>
                <td className="mono">{m.seasons}</td>
                <td className="mono">{m.w}</td><td className="mono">{m.l}</td><td className="mono">{m.t}</td>
                <td className="mono">{m.win_pct != null ? m.win_pct.toFixed(3).replace(/^0/, '') : '—'}</td>
                <td className="mono">{fmt(m.pf)}</td>
                <td className="mono">{m.best_finish ? ord(m.best_finish) : '—'}</td>
                <td className="mono">{m.avg_finish != null ? m.avg_finish.toFixed(1) : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* record book */}
      <div className="section-head">
        <div><span className="eyebrow">Hall of fame &amp; shame</span><h2 className="section-title">The Record Book</h2></div>
      </div>
      <div className="rec-grid">
        {records?.highest_games?.[0] && <Rec label="Highest Score" g={records.highest_games[0]} val={records.highest_games[0].pts} sub={g => `${g.team} · ${g.season} Wk ${g.week} vs ${g.opp}`} />}
        {records?.biggest_blowouts?.[0] && <Rec label="Biggest Blowout" g={records.biggest_blowouts[0]} val={records.biggest_blowouts[0].margin} sub={g => `${g.winner} over ${g.loser} · ${g.season} Wk ${g.week}`} />}
        {records?.top_season_pf?.[0] && <Rec label="Most Points, Season" g={records.top_season_pf[0]} val={records.top_season_pf[0].pf} sub={g => `${g.team} (${g.manager}) · ${g.season}`} />}
        {records?.closest_games?.[0] && <Rec label="Closest Game" g={records.closest_games[0]} val={records.closest_games[0].margin} sub={g => `${g.winner} edged ${g.loser} · ${g.season} Wk ${g.week}`} />}
        {records?.lowest_games?.[0] && <Rec label="Lowest Score" g={records.lowest_games[0]} val={records.lowest_games[0].pts} sub={g => `${g.team} · ${g.season} Wk ${g.week}`} />}
      </div>
    </>
  )
}

function Rec({ label, g, val, sub }) {
  return (
    <div className="rec-card">
      <div className="rlbl">{label}</div>
      <div className="rval tnum">{fmt(val)}</div>
      <div className="rmeta">{sub(g)}</div>
    </div>
  )
}
