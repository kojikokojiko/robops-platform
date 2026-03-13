import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { Dashboard } from './pages/Dashboard'
import { RobotDetail } from './pages/RobotDetail'
import { Schedules } from './pages/Schedules'
import { OTA } from './pages/OTA'

const NAV_ITEMS = [
  { to: '/', label: 'ダッシュボード', end: true },
  { to: '/schedules', label: 'スケジュール' },
  { to: '/ota', label: 'OTA' },
]

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white shadow-sm">
        <div className="mx-auto flex max-w-7xl items-center gap-6 px-4 py-3">
          <span className="text-lg font-bold text-slate-800">🤖 RobOps</span>
          <nav className="flex gap-1">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-50 text-blue-600'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/robots/:robotId" element={<RobotDetail />} />
          <Route path="/schedules" element={<Schedules />} />
          <Route path="/ota" element={<OTA />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
