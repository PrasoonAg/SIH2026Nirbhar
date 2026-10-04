import React from 'react';
import { useAppStore, Theme } from '../../store';
import {
  Sun, Moon, Monitor, Video, VideoOff, Cpu, Sparkles
} from 'lucide-react';

const THEME_OPTIONS: { value: Theme; icon: React.ReactNode; label: string }[] = [
  { value: 'light',  icon: <Sun  size={12} />, label: 'Light'  },
  { value: 'dark',   icon: <Moon size={12} />, label: 'Dark'   },
  { value: 'system', icon: <Monitor size={12} />, label: 'System' },
];

export function TopBar() {
  const { theme, setTheme, recordMode, toggleRecordMode, showcaseMode, setShowcaseMode } = useAppStore();
  const cores = navigator.hardwareConcurrency ?? 4;

  return (
    <header className="topbar app-topbar" role="banner">
      {/* Wordmark */}
      <a href="/" className="topbar-wordmark" aria-label="NIRBHAR Home" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <img src="/favicon.svg" alt="NIRBHAR" width="22" height="22" style={{ borderRadius: 5, flexShrink: 0 }} />
        <span className="topbar-wordmark-latin">NIRBHAR</span>
        <span className="topbar-wordmark-deva">निर्भर</span>
      </a>

      <div className="topbar-divider" aria-hidden />

      {/* Active Solver Engine Badge */}
      <span className="topbar-chip-proto" style={{ background: 'rgba(16, 185, 129, 0.12)', color: 'var(--text)', borderColor: 'rgba(16, 185, 129, 0.4)' }} title="Certified Indigenous Optimization Solver Core — SIH26119 MRPL">
        <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: '#10b981', marginRight: 6 }} />
        SOVEREIGN CORE — Certified Hybrid Optimization Suite
      </span>

      <div className="topbar-spacer" />

      {/* Hardware chip */}
      <span className="topbar-hw-chip" aria-label={`Hardware: ${cores} CPU cores active`}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          <Cpu size={10} style={{ display: 'inline', color: '#10b981' }} />
          {' '}{cores} Cores · Parallel Worker Accelerators
        </span>
      </span>

      <div className="topbar-divider" aria-hidden />

      {/* Showcase Tour Mode */}
      <button
        id="topbar-showcase-mode"
        className={`record-mode-btn${showcaseMode ? ' active' : ''}`}
        onClick={() => setShowcaseMode(!showcaseMode)}
        title="Toggle Guided Showcase Tour — 6-chapter guided walkthrough for judges and reviewers"
        aria-pressed={showcaseMode}
        style={{
          background: showcaseMode ? 'rgba(59, 130, 246, 0.2)' : undefined,
          borderColor: showcaseMode ? 'var(--primary)' : undefined,
          color: showcaseMode ? 'var(--primary)' : undefined
        }}
      >
        <Sparkles size={11} />
        {showcaseMode ? 'Exit Tour' : 'Showcase Tour'}
      </button>

      <div className="topbar-divider" aria-hidden />

      {/* Record mode */}
      <button
        id="topbar-record-mode"
        className={`record-mode-btn${recordMode ? ' active' : ''}`}
        onClick={toggleRecordMode}
        title="Toggle Record Mode — enlarges KPIs and hides dev-only elements for screen recording. Keyboard: M"
        aria-pressed={recordMode}
      >
        {recordMode ? <VideoOff size={11} /> : <Video size={11} />}
        {recordMode ? 'Exit Rec' : 'Rec Mode'}
      </button>

      <div className="topbar-divider" aria-hidden />

      {/* Theme toggle */}
      <div className="theme-toggle" role="group" aria-label="Colour theme">
        {THEME_OPTIONS.map(({ value, icon, label }) => (
          <button
            key={value}
            id={`theme-btn-${value}`}
            className={`theme-toggle-btn${theme === value ? ' active' : ''}`}
            onClick={() => setTheme(value)}
            title={`${label} theme`}
            aria-pressed={theme === value}
          >
            {icon}
          </button>
        ))}
      </div>
    </header>
  );
}
