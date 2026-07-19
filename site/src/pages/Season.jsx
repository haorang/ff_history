import { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAsync, loadSeason, loadIndex, fmt, ord } from '../lib'

const TABS = ['Standings', 'Scores', 'Draft', 'Transactions']

export default function Season() {
  const { year } = useParams()
  const navigate = useNavigate()
  const { data: index } = useAsync(loadIndex, [])
  const { data, loading, error } = useAsync(() => loadSeason(year), [year])
  const [tab, setTab] = useState('Standings')

  if (loading) return <div className="loading"><div className="spinner" />Loading {year}…</div>
  if (error) return <div className="errbox">No data for {year} yet.</div>

  const seasons = index?.seasons || []
  const i = seasons.indexOf(Number(year))
  const prev = i > 0 ? seasons[i - 1] : null
  const next = i >= 0 && i < seasons.length - 1 ? seasons[i + 1] : null

  return (
    <>
      <div className="season-hd">
        <div>
          <span className="eyebrow">{data.num_teams}-team league · {data.reg_weeks}-week regular season</span>
          <h1>{year}</h1>
        </div>
        <div className="season-nav-btns">
          <button className="navbtn" disabled={!prev} onClick={() => prev && navigate(`/season/${prev}`)}>← {prev || ''}</button>
          <button className="navbtn" disabled={!next} onClick={() => next && navigate(`/season/${next}`)}>{next || ''} →</button>
        </div>
      </div>

      <Podium data={data} />

      <div className="tabs">
        {TABS.map((t) => (
          <button key={t} className={`tab ${tab === t ? 'on' : ''}`} onClick={() => setTab(t)}>{t}</button>
        ))}
      </div>

      {tab === 'Standings' && <Standings data={data} />}
      {tab === 'Scores' && <Scores data={data} />}
      {tab === 'Draft' && <Draft data={data} />}
      {tab === 'Transactions' && <Transactions data={data} />}
    </>
  )
}

function Podium({ data }) {
  const spots = [
    ['1st', data.champion, 'p1'],
    ['2nd', data.runner_up, 'p2'],
    ['3rd', data.third, 'p3'],
  ].filter((s) => s[1])
  if (!spots.length) return null
  return (
    <div className="podium">
      {spots.map(([place, t, cls]) => (
        <div key={place} className={`p ${cls}`}>
          <div className="place">{cls === 'p1' ? '🏆 Champion' : `${place} Place`}</div>
          <div className="pteam">{t.team}</div>
          <div className="pwho">{t.manager}</div>
        </div>
      ))}
    </div>
  )
}

function Standings({ data }) {
  return (
    <>
      <div className="table-wrap">
        <table className="grid">
          <thead>
            <tr>
              <th style={{ width: 34 }}></th><th className="l">Team</th>
              <th>Record</th><th>Pct</th><th>Streak</th><th>Points For</th><th>Points Against</th>
            </tr>
          </thead>
          <tbody>
            {data.standings.map((r) => (
              <tr key={r.rank} className={r.rank <= 6 ? 'is-playoff' : ''}>
                <td className="rankcell">{r.rank}</td>
                <td className="l teamcell">{r.team}<small>{r.manager}</small></td>
                <td className="mono">{r.record}</td>
                <td className="mono">{r.pct}</td>
                <td className="mono">{r.streak}</td>
                <td className="mono">{fmt(r.pf)}</td>
                <td className="mono">{fmt(r.pa)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.final?.length > 0 && (
        <>
          <div className="section-head"><div><span className="eyebrow">After the playoffs</span><h2 className="section-title" style={{ fontSize: 22 }}>Final Finish</h2></div></div>
          <div className="board">
            {data.final.map((r) => (
              <div key={r.place} className="pick">
                <div className="ov" style={{ color: r.place <= 3 ? 'var(--gold)' : 'var(--faint)' }}>{r.place}</div>
                <div><div className="pl">{r.team}{r.place === 1 ? <span className="cup-sm">🏆</span> : ''}</div><div className="to">{r.manager}</div></div>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  )
}

function Scores({ data }) {
  const weekKeys = useMemo(() => Object.keys(data.weeks).sort((a, b) => a - b), [data])
  const [wk, setWk] = useState(weekKeys[0])
  const [open, setOpen] = useState(null)
  if (!weekKeys.length) return <div className="box-na">No schedule captured for this season.</div>
  const week = data.weeks[wk]

  return (
    <>
      <div className="week-picker">
        {weekKeys.map((k) => (
          <button key={k} className={`wk ${wk === k ? 'on' : ''} ${data.weeks[k].playoff ? 'po' : ''}`}
            onClick={() => { setWk(k); setOpen(null) }}>{k}</button>
        ))}
      </div>
      {week.playoff && <div style={{ marginBottom: 12 }}><span className="pill playoff">Playoffs</span></div>}
      <div className="matchups">
        {week.matchups.map((m, idx) => {
          const aWon = m.pts_a >= m.pts_b
          const isOpen = open === idx
          return (
            <div key={idx} className={`mrow ${isOpen ? 'open' : ''}`}>
              <button onClick={() => setOpen(isOpen ? null : idx)}>
                <div className={`mside ${aWon ? 'won' : 'lost'}`}>
                  <div className="nm"><b>{m.team_a}</b><small>{m.mgr_a}</small></div>
                  <span className="mscore tnum">{fmt(m.pts_a)}</span>
                </div>
                <div className="mmid">WK {wk}<span className="caret">▼</span></div>
                <div className={`mside right ${!aWon ? 'won' : 'lost'}`}>
                  <span className="mscore tnum">{fmt(m.pts_b)}</span>
                  <div className="nm"><b>{m.team_b}</b><small>{m.mgr_b}</small></div>
                </div>
              </button>
              {isOpen && <BoxScore data={data} wk={wk} a={m.team_a} b={m.team_b} />}
            </div>
          )
        })}
      </div>
    </>
  )
}

function BoxScore({ data, wk, a, b }) {
  const week = data.boxscores[wk] || {}
  const A = week[a], B = week[b]
  if (!A || !B) return <div className="box-na">Box score not available for this matchup.</div>
  const aWin = A.total >= B.total
  return (
    <div className="box">
      <TeamBox t={A} name={a} win={aWin} />
      <TeamBox t={B} name={b} win={!aWin} />
    </div>
  )
}

function TeamBox({ t, name, win }) {
  return (
    <div className={`boxteam ${win ? 'win' : ''}`}>
      <h4><span>{name}</span><span className="bt tnum">{fmt(t.total)}</span></h4>
      {t.starters.map((p, i) => <PlayerRow key={i} p={p} />)}
      {t.bench?.length > 0 && <>
        <div className="bench-lbl">Bench</div>
        {t.bench.map((p, i) => <PlayerRow key={i} p={p} bench />)}
      </>}
    </div>
  )
}

function PlayerRow({ p, bench }) {
  return (
    <div className={`plr ${bench ? 'bn' : ''}`}>
      <span className="pos">{p.pos}</span>
      <span className="pn">{p.name}{p.nfl ? <i>{p.nfl}</i> : ''}</span>
      <span className="pp">{fmt(p.pts)}</span>
    </div>
  )
}

function Draft({ data }) {
  const rounds = useMemo(() => [...new Set(data.draft.map((p) => p.round))].sort((a, b) => a - b), [data])
  const [r, setR] = useState(rounds[0])
  if (!data.draft.length) return <div className="box-na">Draft results not captured for this season.</div>
  const picks = data.draft.filter((p) => p.round === r)
  return (
    <>
      <div className="draft-rounds">
        {rounds.map((rd) => (
          <button key={rd} className={`wk ${r === rd ? 'on' : ''}`} onClick={() => setR(rd)}>{rd}</button>
        ))}
      </div>
      <div className="board">
        {picks.map((p) => (
          <div key={p.overall} className="pick">
            <div className="ov">{p.overall}</div>
            <div>
              <div className="pl">{p.player}{p.pos_team ? <i>{p.pos_team}</i> : ''}</div>
              <div className="to">→ {p.team} · {p.manager}</div>
            </div>
          </div>
        ))}
      </div>
    </>
  )
}

const TXN_FILTERS = ['All', 'Add', 'Drop', 'Trade', 'Lineup']

function Transactions({ data }) {
  const [f, setF] = useState('All')
  const [limit, setLimit] = useState(40)
  if (!data.transactions.length) return <div className="box-na">Transactions not captured for this season.</div>
  const filtered = f === 'All' ? data.transactions : data.transactions.filter((t) => t.type === f)
  const shown = filtered.slice(0, limit)
  return (
    <>
      <div className="txn-filter">
        {TXN_FILTERS.map((x) => (
          <button key={x} className={`fchip ${f === x ? 'on' : ''}`} onClick={() => { setF(x); setLimit(40) }}>{x}</button>
        ))}
        <span className="faint" style={{ alignSelf: 'center', fontFamily: 'var(--cond)', fontSize: 13 }}>{filtered.length} moves</span>
      </div>
      <div className="txn-list">
        {shown.map((t, i) => (
          <div key={i} className="txn">
            <span className="tdate">{t.date}</span>
            <span className={`ttype ${t.type.toLowerCase()}`}>{t.type}</span>
            <span className="tbody">
              <b>{t.player}</b>{' '}
              <span className="flow">· {t.from} → {t.to}</span>{' '}
              <span className="tby">— {t.by}</span>
            </span>
          </div>
        ))}
      </div>
      {limit < filtered.length && (
        <button className="more-btn" onClick={() => setLimit(limit + 60)}>Show more ({filtered.length - limit} left)</button>
      )}
    </>
  )
}
