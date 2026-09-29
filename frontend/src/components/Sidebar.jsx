// components/Sidebar.jsx
import { NavLink } from 'react-router-dom'
import {
  Upload,
  Server,
  Cpu,
  GitBranch,
  ShieldCheck,
  Wrench,
  FileText,
  ShieldAlert,
  ListChecks,
} from 'lucide-react'

const NAV_ITEMS = [
  { section: 'Ingest & Triage' },
  { path: '/',         label: 'Upload & Ingest',     icon: Upload,      tier: 'T1' },
  { path: '/fleet',    label: 'Fleet Triage',        icon: Server,      tier: 'T1' },

  { section: 'Self-Teaching Engine' },
  { path: '/training', label: 'Training Studio',     icon: Cpu,         tier: 'T1' },
  { path: '/mapping',  label: 'Mapping Lifecycle',   icon: GitBranch,   tier: 'T1' },
  { path: '/selfaudit',label: 'Self-Audit',          icon: ShieldCheck, tier: 'T1' },

  { section: 'Remediation & Reports' },
  { path: '/fiximpact',label: 'Fix-Impact Sandbox',  icon: Wrench,      tier: 'T2' },
  { path: '/reports',  label: 'Reports & Export',    icon: FileText,    tier: 'T1' },

  { section: 'Governance & Invariants' },
  { path: '/ledger',   label: 'Ledger & Alerts',     icon: ShieldAlert, tier: 'T1' },
  { path: '/features', label: 'Feature Registry',    icon: ListChecks,  tier: 'INV-14' },
]

export default function Sidebar() {
  return (
    <aside className="sidebar">
      {/* Brand Header */}
      <div className="sidebar-logo">
        <div className="logo-glyph">प्र</div>
        <div>
          <div className="logo-text">PRAMANA</div>
          <div className="logo-sub">AUDIT ENGINE · NTRO</div>
        </div>
      </div>

      {/* Nav List */}
      <nav className="nav">
        {NAV_ITEMS.map((item, index) => {
          if (item.section) {
            return (
              <div key={`sec-${index}`} className="nav-section">
                {item.section}
              </div>
            )
          }

          const IconComponent = item.icon
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <IconComponent className="nav-icon" />
              <span>{item.label}</span>
              {item.tier && (
                <span className={`nav-tier ${item.tier === 'T2' ? 'feat-badge t2' : ''}`}>
                  {item.tier}
                </span>
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* Footer / Offline Badge (INV-11) */}
      <div className="sidebar-footer">
        <div className="offline-badge">
          <span className="offline-dot" />
          <span>AIR-GAPPED · ZERO EGRESS</span>
        </div>
        <div className="txt-3 mt-1" style={{ fontSize: '.62rem', fontFamily: 'var(--mono)' }}>
          v0.1.0-alpha · 203 PASS
        </div>
      </div>
    </aside>
  )
}
