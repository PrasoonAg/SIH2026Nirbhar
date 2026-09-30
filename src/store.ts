import { create } from 'zustand';

export type Theme = 'light' | 'dark' | 'system';

function applyTheme(theme: Theme) {
  const root = document.documentElement;
  if (theme === 'system') {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    root.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
  } else {
    root.setAttribute('data-theme', theme);
  }
}

interface AppState {
  theme: Theme;
  recordMode: boolean;
  showcaseMode: boolean;
  showcaseChapter: number;
  setTheme: (theme: Theme) => void;
  toggleRecordMode: () => void;
  setShowcaseMode: (active: boolean) => void;
  setShowcaseChapter: (chapter: number) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // First load is always Light per spec (§3)
  theme: 'light',
  recordMode: false,
  showcaseMode: false,
  showcaseChapter: 0,

  setTheme: (theme) => {
    set({ theme });
    applyTheme(theme);
    try { localStorage.setItem('nirbhar-theme', theme); } catch {}
  },

  toggleRecordMode: () => set((s) => {
    const next = !s.recordMode;
    document.documentElement.setAttribute('data-record-mode', String(next));
    return { recordMode: next };
  }),

  setShowcaseMode: (active) => set({ showcaseMode: active, showcaseChapter: active ? 0 : 0 }),
  setShowcaseChapter: (chapter) => set({ showcaseChapter: chapter }),
}));

// Initialize theme on module load (always Light on first load)
(() => {
  // Always start Light regardless of OS preference (spec §3 rule)
  document.documentElement.setAttribute('data-theme', 'light');
  // Restore user's saved preference for subsequent loads
  try {
    const saved = localStorage.getItem('nirbhar-theme') as Theme | null;
    if (saved && ['light', 'dark', 'system'].includes(saved)) {
      applyTheme(saved);
      // But we don't call setTheme here — the store default is 'light'
      // The store will be hydrated from the initial render
    }
  } catch {}
})();
