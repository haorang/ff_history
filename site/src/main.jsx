import React from 'react'
import ReactDOM from 'react-dom/client'
import { HashRouter, Routes, Route } from 'react-router-dom'
import './styles.css'
import App from './App'
import Home from './pages/Home'
import Season from './pages/Season'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <HashRouter>
      <Routes>
        <Route path="/" element={<App />}>
          <Route index element={<Home />} />
          <Route path="season/:year" element={<Season />} />
        </Route>
      </Routes>
    </HashRouter>
  </React.StrictMode>
)
