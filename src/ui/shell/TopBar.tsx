import React from 'react';
import { useAppStore, Theme } from '../../store';
import {
  Sun, Moon, Monitor, Video, VideoOff, Cpu,
} from 'lucide-react';

const THEME_OPTIONS: { value: Theme; icon: React.ReactNode; label: string }[] = [
  { value: 'light',  icon: <Sun  size={12} />, label: 'Light'  },
  { value: 'dark',   icon: <Moon size={12} />, label: 'Dark'   },
  { value: 'system', icon: <Monitor size={12} />, label: 'System' },
];

export function TopBar() {
  const { theme, setTheme, recordMode, toggleRecordMode } = useAppStore();
  const cores = navigator.hardwareConcurrency ?? 4;

  return (
    <header className="topbar app-topbar" role="banner">
      {/* Wordmark */}
      <a href="/" className="topbar-wordmark" aria-label="NIRBHAR Home">
        <span className="topbar-wordmark-latin">NIRBHAR</span>
        <span className="topbar-wordmark-deva">निर्भर</span>
      </a>

      <div className="topbar-divider" aria-hidden />

      {/* Prototype badge */}
      <span className="topbar-chip-proto" title="All computation runs in your browser as CPU JavaScript. Production NIRBHAR uses Python + Numba + JAX on CPU/GPU/TPU.">
        PROTOTYPE — engines run as CPU JavaScript in your browser
      </span>

      <div className="topbar-spacer" />

      {/* Hardware chip */}
      <span className="topbar-hw-chip" aria-label={`Hardware: ${cores} CPU cores, no GPU used`}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          <Cpu size={10} style={{ display: 'inline' }} />
          {' '}{cores} cores · GPU: none (CPU-JS prototype)
        </span>
      </span>

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
