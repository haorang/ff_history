import { useEffect, useState } from 'react'

// ---- edit these to rename the league ----------------------------------------
export const LEAGUE_NAME = 'Mr Blue Sky'
export const LEAGUE_TAGLINE = 'Fantasy Football Almanac'
// -----------------------------------------------------------------------------

const BASE = import.meta.env.BASE_URL
const cache = {}

export async function loadJSON(name) {
  if (cache[name]) return cache[name]
  const res = await fetch(`${BASE}data/${name}`)
  if (!res.ok) throw new Error(`Could not load ${name} (${res.status})`)
  const json = await res.json()
  cache[name] = json
  return json
}

export const loadIndex = () => loadJSON('index.json')
export const loadSeason = (year) => loadJSON(`${year}.json`)

// small formatting helpers
export const fmt = (n, d = 2) =>
  n == null ? '—' : Number(n).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d })

export const ord = (n) => {
  const s = ['th', 'st', 'nd', 'rd'], v = n % 100
  return n + (s[(v - 20) % 10] || s[v] || s[0])
}

export const yy = (year) => `’${String(year).slice(2)}`

// generic async data hook
export function useAsync(fn, deps = []) {
  const [state, setState] = useState({ loading: true, data: null, error: null })
  useEffect(() => {
    let alive = true
    setState({ loading: true, data: null, error: null })
    Promise.resolve()
      .then(fn)
      .then((data) => alive && setState({ loading: false, data, error: null }))
      .catch((error) => alive && setState({ loading: false, data: null, error }))
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return state
}
