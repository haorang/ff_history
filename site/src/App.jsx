import { Link, NavLink, Outlet } from 'react-router-dom'
import { useAsync, loadIndex, LEAGUE_NAME, LEAGUE_TAGLINE, yy } from './lib'

export default function App() {
  const { data: index } = useAsync(loadIndex, [])
  const seasons = index?.seasons || []

  return (
    <div className="app">
      <header className="topbar">
        <div className="bar-inner">
          <Link to="/" className="brand">
            <span className="brand-mark">🏈</span>
            <span className="brand-txt">
              <b>{LEAGUE_NAME}</b>
              <i>{LEAGUE_TAGLINE}</i>
            </span>
          </Link>
          <nav className="seasons-nav" aria-label="Seasons">
            {seasons.map((s) => (
              <NavLink key={s} to={`/season/${s}`} className="season-pill">
                {yy(s)}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="content">
        <Outlet />
      </main>

      <footer className="site-foot">
        <span>Archived from NFL.com before the ESPN migration</span>
        {seasons.length > 0 && (
          <span className="foot-years">{seasons[0]} – {seasons[seasons.length - 1]}</span>
        )}
      </footer>
    </div>
  )
}
