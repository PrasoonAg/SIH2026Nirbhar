// App.jsx — PRAMANA Frontend Application Shell
// Router configuration wiring all 9 screens from §11
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Upload from './pages/Upload'
import Fleet from './pages/Fleet'
import Training from './pages/Training'
import Mapping from './pages/Mapping'
import SelfAudit from './pages/SelfAudit'
import FixImpact from './pages/FixImpact'
import Reports from './pages/Reports'
import Ledger from './pages/Ledger'
import FeatureRegistry from './pages/FeatureRegistry'
import DemoReset from './components/DemoReset'

const ROUTE_TITLES = {
  '/':           { title: 'Configuration Ingest & Audit', subtitle: 'Screen 1 · Single/ZIP Ingestion with Security Guards' },
  '/fleet':      { title: 'Fleet Compliance Dashboard',  subtitle: 'Screen 2 · Triage, Two-Number Scores & Blast-Radius Flags' },
  '/training':   { title: 'Offline Training Studio',     subtitle: 'Screen 3 · Cosine Anchors, Slot Editor & Gate Panel' },
  '/mapping':    { title: 'Mapping State Machine',       subtitle: 'Screen 4 · State Lifecycle & Gate Evidence Ledger (INV-01)' },
  '/selfaudit':  { title: 'Trust Mechanism Self-Audit',  subtitle: 'Screen 5 · Empirical Rates, Wilson CIs & Residual Risk (INV-15)' },
  '/fiximpact':  { title: 'Fix-Impact Sandbox',          subtitle: 'Screen 6 · Ranked Queue & Verified Remediation Delta (T2 Planned)' },
  '/reports':    { title: 'Audit Reports & Evidence',    subtitle: 'Screen 7 · Per-Device PDF, Appendix A & Appendix B' },
  '/ledger':     { title: 'Ledger & Security Alerts',    subtitle: 'Screen 8 · Hash-Chained Audit Trail & Demotion Alerts (INV-12)' },
  '/features':   { title: 'Feature Registry & Invariants', subtitle: 'Screen 9 · Honest Tiering & Constitutional Invariants (INV-14)' },
}

export default function App() {
  const location = useLocation()
  const currentMeta = ROUTE_TITLES[location.pathname] || { title: 'PRAMANA Network Audit', subtitle: 'Offline Multi-Vendor Compliance Engine' }

  return (
    <div className="shell">
      <DemoReset />
      {/* Navigation Sidebar */}
      <Sidebar />

      {/* Main View Area */}
      <div className="main-content">
        {/* Sticky Topbar */}
        <header className="topbar">
          <div>
            <div className="topbar-title">{currentMeta.title}</div>
            <div className="topbar-meta">{currentMeta.subtitle}</div>
          </div>
          <div className="flex items-center gap-2">
            <span className="txt-mono txt-3" style={{ fontSize: '.72rem' }}>
              PROFILE <span className="txt-2">git:abc1234</span>
            </span>
            <span className="txt-3">·</span>
            <span className="txt-mono txt-3" style={{ fontSize: '.72rem' }}>
              GATE <span style={{ color: 'var(--accent-green)' }}>ACTIVE (3/3)</span>
            </span>
            <span className="txt-3">·</span>
            <span className="trust-badge det" style={{ fontSize: '.6rem' }}>
              AIR-GAPPED
            </span>
          </div>
        </header>

        {/* Dynamic Screen Routes */}
        <Routes>
          <Route path="/" element={<Upload />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/fleet" element={<Fleet />} />
          <Route path="/training" element={<Training />} />
          <Route path="/mapping" element={<Mapping />} />
          <Route path="/selfaudit" element={<SelfAudit />} />
          <Route path="/fiximpact" element={<FixImpact />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/ledger" element={<Ledger />} />
          <Route path="/features" element={<FeatureRegistry />} />
          {/* Catch-all fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </div>
  )
}
