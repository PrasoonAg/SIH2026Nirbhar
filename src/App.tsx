import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { TopBar } from './ui/shell/TopBar';
import { NavRail } from './ui/shell/NavRail';

// Lazy-load all pages for code splitting
const Home          = lazy(() => import('./ui/pages/Home'));
const SolveStudio   = lazy(() => import('./ui/pages/SolveStudio'));
const RefineryDemo  = lazy(() => import('./ui/pages/RefineryDemo'));
const BranchCutLab  = lazy(() => import('./ui/pages/BranchCutLab'));
const RobustnessLab = lazy(() => import('./ui/pages/RobustnessLab'));
const Verifier      = lazy(() => import('./ui/pages/Verifier'));
const Benchmarks    = lazy(() => import('./ui/pages/Benchmarks'));
const ModelFamilies = lazy(() => import('./ui/pages/ModelFamilies'));
const Architecture  = lazy(() => import('./ui/pages/Architecture'));
const CliApi        = lazy(() => import('./ui/pages/CliApi'));
const PSCompliance  = lazy(() => import('./ui/pages/PSCompliance'));
const SelfTest      = lazy(() => import('./ui/pages/SelfTest'));

function PageLoader() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
      <div className="spinner" style={{ marginRight: 8 }} />
      Loading…
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <TopBar />
        <NavRail />
        <main className="app-main" id="main-content" role="main">
          <Suspense fallback={<PageLoader />}>
            <Routes>
              <Route path="/"             element={<Home />} />
              <Route path="/studio/*"     element={<SolveStudio />} />
              <Route path="/refinery/*"   element={<RefineryDemo />} />
              <Route path="/bnc-lab/*"    element={<BranchCutLab />} />
              <Route path="/robustness/*" element={<RobustnessLab />} />
              <Route path="/verifier/*"   element={<Verifier />} />
              <Route path="/benchmarks/*" element={<Benchmarks />} />
              <Route path="/families/*"   element={<ModelFamilies />} />
              <Route path="/architecture/*" element={<Architecture />} />
              <Route path="/cli/*"        element={<CliApi />} />
              <Route path="/compliance/*" element={<PSCompliance />} />
              <Route path="/selftest"     element={<SelfTest />} />
            </Routes>
          </Suspense>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
