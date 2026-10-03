import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  Home, FlaskConical, TreePine, Shield, CheckSquare,
  BarChart3, Layers, Network, Terminal, FileCheck2,
  TestTube2, Zap,
} from 'lucide-react';

interface NavEntry {
  path: string;
  label: string;
  icon: React.ReactNode;
  id: string;
}

const NAV_ITEMS: NavEntry[] = [
  { path: '/',             label: 'Home',              icon: <Home      size={15} />, id: 'nav-home' },
  { path: '/studio',       label: 'Solve Studio',      icon: <Zap       size={15} />, id: 'nav-studio' },
  { path: '/refinery',     label: 'Refinery Demo',     icon: <FlaskConical size={15} />, id: 'nav-refinery' },
  { path: '/bnc-lab',      label: 'Branch-and-Cut Lab',icon: <TreePine  size={15} />, id: 'nav-bnc' },
  { path: '/robustness',   label: 'Robustness Lab',    icon: <Shield    size={15} />, id: 'nav-robust' },
  { path: '/verifier',     label: 'Verifier',          icon: <CheckSquare size={15} />, id: 'nav-verify' },
  { path: '/benchmarks',   label: 'Benchmarks',        icon: <BarChart3 size={15} />, id: 'nav-bench' },
  { path: '/families',     label: 'Model Families',    icon: <Layers    size={15} />, id: 'nav-families' },
  { path: '/architecture', label: 'Architecture',      icon: <Network   size={15} />, id: 'nav-arch' },
  { path: '/cli',          label: 'CLI and API',        icon: <Terminal  size={15} />, id: 'nav-cli' },
  { path: '/compliance',   label: 'PS Compliance',     icon: <FileCheck2 size={15} />, id: 'nav-compliance' },
  { path: '/selftest',     label: 'Self-Test',         icon: <TestTube2 size={15} />, id: 'nav-selftest' },
];

export function NavRail() {
  const location = useLocation();

  return (
    <nav className="nav-rail app-nav" aria-label="Main navigation">
      <div className="nav-section-label">Navigation</div>
      {NAV_ITEMS.map(({ path, label, icon, id }) => {
        const isActive = path === '/'
          ? location.pathname === '/'
          : location.pathname.startsWith(path);
        return (
          <NavLink
            key={path}
            to={path}
            id={id}
            className={`nav-item${isActive ? ' active' : ''}`}
            aria-current={isActive ? 'page' : undefined}
            end={path === '/'}
          >
            <span className="nav-item-icon" aria-hidden>{icon}</span>
            <span>{label}</span>
          </NavLink>
        );
      })}
    </nav>
  );
}
