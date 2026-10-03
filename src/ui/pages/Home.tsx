import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Play, Cpu, Shield, CheckSquare, GitBranch, Zap,
  FlaskConical, BarChart3, Layers, Terminal, FileCheck2,
  ChevronRight, Lock, Activity,
} from 'lucide-react';
import { useAppStore } from '../../store';

// The 8 "what is ours" cards matching §11.1
const WHAT_IS_OURS = [
  {
    icon: <Shield size={18} />,
    title: 'Certified Bounds',
    body: 'Every answer carries a dual-certified lower bound LB(y) evaluated in the original unscaled model space. OPTIMAL is displayed only when gap ≤ tolerance AND the independent verifier returns PASS.',
  },
  {
    icon: <Lock size={18} />,
    title: 'Independent Verifier',
    body: 'A completely isolated verification engine (src/verify) with its own MPS reader and bound code — no imports from the solver. Runs in float64 or exact BigInt rational arithmetic.',
  },
  {
    icon: <GitBranch size={18} />,
    title: 'Certified Branch-and-Cut',
    body: 'Every prune uses a safe bound. Every infeasible node is backed by a Farkas ray. Cuts carry derivation records re-checked in exact arithmetic. No node is pruned without a recorded certificate.',
  },
  {
    icon: <Activity size={18} />,
    title: 'Concurrent Root Race',
    body: 'Dual simplex, interior point, and HPR-family engines run in parallel Web Workers. The first to produce a verified result wins; the others are terminated. Results are never mixed.',
  },
  {
    icon: <Zap size={18} />,
    title: 'Sovereign Solver Core',
    body: 'src/solver and src/verify import zero third-party numeric or solver packages. Verified at build time by check-imports. The Sovereignty panel shows its real output.',
  },
  {
    icon: <CheckSquare size={18} />,
    title: 'Honest Status Labels',
    body: 'Status levels: OPTIMAL, OPTIMAL_WITHIN_GAP, CERTIFIED_APPROXIMATE, INFEASIBLE_CERTIFIED, UNBOUNDED_CERTIFIED, TIME_LIMIT, NUMERICAL_ISSUE, UNSUPPORTED, LOCAL_ONLY. Never overclaimed.',
  },
  {
    icon: <Cpu size={18} />,
    title: 'HPR-Family First-Order Engine',
    body: 'A Halpern-anchored primal–dual first-order engine for LP, QP, and batched scenarios. Labelled HPR-family (CPU-JS here; JAX/GPU in production). Provides certified approximate bounds.',
  },
  {
    icon: <Layers size={18} />,
    title: 'Plug-in Architecture',
    body: 'Eight interfaces: Engine, Presolver, Propagator, BranchingRule, NodeSelector, Heuristic, CutGenerator, ModelClass. NIRBHAR itself registers through the same registry. Live demo included.',
  },
];

const DEMO_CHAPTERS = [
  { num: '01', title: 'Refinery LP', desc: 'Race → winner → certificate → verifier PASS', path: '/refinery' },
  { num: '02', title: 'Refinery MILP', desc: 'Live B&C tree, cuts, gap converging, brute-force MATCH', path: '/bnc-lab' },
  { num: '03', title: 'Refinery QP', desc: 'IPM vs HPR-family, closed-form bound, non-convex refusal', path: '/refinery' },
  { num: '04', title: 'Scenario Batch', desc: 'Sequential vs pool vs batched HPR, honest break-even chart', path: '/refinery' },
];

export default function Home() {
  const navigate = useNavigate();
  const { setShowcaseMode } = useAppStore();

  function startDemo() {
    setShowcaseMode(true);
    navigate('/refinery');
  }

  return (
    <div className="page" style={{ paddingBottom: 48 }}>
      {/* Hero */}
      <section style={{ marginBottom: 'var(--space-8)' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-6)', flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 400px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
              <span className="badge-synthetic">SYNTHETIC — not MRPL data</span>
              <span className="badge-prototype">PROTOTYPE — CPU JavaScript</span>
            </div>
            <h1 className="text-page" style={{ marginBottom: 'var(--space-3)', lineHeight: 1.2 }}>
              NIRBHAR — निर्भर
            </h1>
            <p style={{ fontSize: 18, fontWeight: 500, color: 'var(--primary)', marginBottom: 'var(--space-4)' }}>
              The solver that proves its answers.
            </p>
            <p style={{ fontSize: 14, color: 'var(--text-muted)', maxWidth: 560, lineHeight: 1.7, marginBottom: 'var(--space-6)' }}>
              An indigenous certified hybrid CPU–GPU optimization solver core. Every result is backed by a dual lower bound evaluated
              on the original model and independently verified. NIRBHAR solves LP, MILP, QP, and MIQP problems — and
              never displays OPTIMAL unless the gap is within tolerance <em>and</em> the verifier returns PASS.
            </p>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', maxWidth: 560, lineHeight: 1.6, marginBottom: 'var(--space-6)', padding: '12px 16px', background: 'var(--surface-2)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
              <strong style={{ color: 'var(--text)' }}>Smart India Hackathon 2026</strong> · PS SIH26119 · Team Vernils · MRPL
              <br />
              Solver target: refinery planning and scheduling for Mangalore Refinery and Petrochemicals Limited.
            </p>
            <div style={{ display: 'flex', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
              <button id="home-start-demo" className="btn btn-primary btn-lg" onClick={startDemo}>
                <Play size={16} /> Start 2-minute demo
              </button>
              <button id="home-run-selftest" className="btn btn-secondary btn-lg" onClick={() => navigate('/selftest')}>
                <CheckSquare size={16} /> Run self-test
              </button>
            </div>
          </div>

          {/* Core path preview */}
          <div className="card" style={{ flex: '0 0 320px', padding: 'var(--space-5)' }}>
            <div className="text-label" style={{ marginBottom: 'var(--space-4)' }}>Core demo path (≈ 2 min)</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {DEMO_CHAPTERS.map((ch) => (
                <div
                  key={ch.num}
                  style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-3)', cursor: 'pointer', padding: '8px 10px', borderRadius: 'var(--radius-md)', transition: 'background var(--transition-fast)' }}
                  onClick={() => navigate(ch.path)}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--surface-2)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700, color: 'var(--accent)', minWidth: 24, paddingTop: 2 }}>{ch.num}</span>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 550, color: 'var(--text)' }}>{ch.title}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{ch.desc}</div>
                  </div>
                  <ChevronRight size={14} style={{ marginLeft: 'auto', color: 'var(--text-muted)', flexShrink: 0, marginTop: 2 }} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* What is ours — 8 cards */}
      <section style={{ marginBottom: 'var(--space-8)' }}>
        <h2 className="text-section" style={{ marginBottom: 'var(--space-4)' }}>What is genuinely ours</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 'var(--space-4)' }}>
          {WHAT_IS_OURS.map(({ icon, title, body }) => (
            <div key={title} className="card" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--primary)' }}>
                {icon}
                <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>{title}</span>
              </div>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.6 }}>{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Quick links */}
      <section>
        <h2 className="text-section" style={{ marginBottom: 'var(--space-4)' }}>Pages</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 'var(--space-3)' }}>
          {[
            { icon: <Zap size={15} />,         label: 'Solve Studio',       path: '/studio',       desc: 'General LP/MILP/QP solver' },
            { icon: <FlaskConical size={15} />, label: 'Refinery Demo',      path: '/refinery',     desc: 'Guided LP → MILP → QP → Batch' },
            { icon: <GitBranch size={15} />,    label: 'Branch-and-Cut Lab', path: '/bnc-lab',      desc: 'Live tree, cuts, heuristics' },
            { icon: <Shield size={15} />,       label: 'Robustness Lab',     path: '/robustness',   desc: 'Naive vs hardened comparison' },
            { icon: <CheckSquare size={15} />,  label: 'Verifier',           path: '/verifier',     desc: 'Independent float + exact check' },
            { icon: <BarChart3 size={15} />,    label: 'Benchmarks',         path: '/benchmarks',   desc: 'Netlib, MILP, QP tables' },
            { icon: <Layers size={15} />,       label: 'Model Families',     path: '/families',     desc: 'Refinery, transport, power, …' },
            { icon: <Terminal size={15} />,     label: 'CLI and API',         path: '/cli',          desc: 'In-browser terminal' },
            { icon: <FileCheck2 size={15} />,   label: 'PS Compliance',      path: '/compliance',   desc: 'SIH26119 traceability matrix' },
          ].map(({ icon, label, path, desc }) => (
            <button
              key={path}
              className="card"
              style={{ display: 'flex', flexDirection: 'column', gap: 6, cursor: 'pointer', border: '1px solid var(--border)', background: 'var(--surface)', textAlign: 'left', transition: 'box-shadow var(--transition-fast)' }}
              onClick={() => navigate(path)}
              onMouseEnter={(e) => (e.currentTarget.style.boxShadow = 'var(--shadow-popover)')}
              onMouseLeave={(e) => (e.currentTarget.style.boxShadow = 'none')}
            >
              <div style={{ color: 'var(--primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                {icon}
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{label}</span>
              </div>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{desc}</span>
            </button>
          ))}
        </div>
      </section>

      {/* Honesty footer */}
      <div style={{ marginTop: 'var(--space-10)', padding: 'var(--space-4)', background: 'var(--surface-2)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.7 }}>
        <strong style={{ color: 'var(--text)', display: 'block', marginBottom: 4 }}>About this prototype</strong>
        All computation in this prototype runs in your browser as CPU JavaScript in Web Workers.
        The "HPR-family" engine is a Halpern-anchored PDHG-type first-order operator (CPU-JS here; JAX/GPU in production).
        All refinery and planning models carry a SYNTHETIC tag — they are generated, not MRPL operational data.
        Any number not measured in this prototype appears only in a PRODUCTION TARGET chip and is never displayed as a result.
        See <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text)' }}>KNOWN_LIMITS.md</span> for a complete list of what this prototype does not do.
      </div>
    </div>
  );
}
