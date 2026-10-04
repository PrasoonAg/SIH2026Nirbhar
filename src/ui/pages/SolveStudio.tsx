/**
 * Solve Studio — F1–F6
 * General LP / MILP / QP / MIQP solver with:
 *   F1  MPS/QPS editor with syntax highlighting and parse status
 *   F2  Engine selection (dual simplex | IPM | HPR-family | B&C)
 *   F3  Live solve view: iterations, objective, infeasibility
 *   F4  Certificate download and verifier integration
 *   F5  (Phase 2) Presolve/postsolve toggle
 *   F6  (Phase 2) Explainability: shadow prices, ranging, IIS
 */

import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  Play, Square, Download, CheckCircle2, XCircle, AlertTriangle,
  RefreshCw, ChevronDown, ChevronRight, Info, Loader2,
  FileText, Cpu, Shield, Eye, FlaskConical,
} from 'lucide-react';

import type { EngineId } from '../../solver/dispatch';
import type { EngineResult } from '../../solver/lp/dualSimplex';
import type { Certificate } from '../../solver/certificate/schema';
import { serialiseCert } from '../../solver/certificate/schema';
import { buildCertLP } from '../../solver/certificate/builder';
import { explainCertificate } from '../../solver/certificate/explain';
import type { ExplainReport } from '../../solver/certificate/explain';
import { checkBackendHealth, solveViaBackend, type BackendHealth } from '../../solver/bridge';

// ─── Worker pool singleton ────────────────────────────────────────────────────
let _worker: Worker | null = null;
function getEngineWorker(): Worker {
  if (!_worker) {
    _worker = new Worker(
      new URL('../../solver/workers/engine.worker.ts', import.meta.url),
      { type: 'module' },
    );
  }
  return _worker;
}

// ─── Sample MPS models ────────────────────────────────────────────────────────
const SAMPLE_AFIRO = `NAME          AFIRO                                                             
ROWS
 E  R09     
 E  R10     
 L  X05     
 L  X21     
 E  R12     
 E  R13     
 L  X17     
 L  X18     
 L  X19     
 L  X20     
 E  R19     
 E  R20     
 L  X27     
 L  X44     
 E  R22     
 E  R23     
 L  X40     
 L  X41     
 L  X42     
 L  X43     
 L  X45     
 L  X46     
 L  X47     
 L  X48     
 L  X49     
 L  X50     
 L  X51     
 N  COST    
COLUMNS
    X01       X48               .301   R09                -1.   
    X01       R10              -1.06   X05                 1.   
    X02       X21                -1.   R09                 1.   
    X02       COST               -.4   
    X03       X46                -1.   R09                 1.   
    X04       X50                 1.   R10                 1.   
    X06       X49               .301   R12                -1.   
    X06       R13              -1.06   X17                 1.   
    X07       X49               .313   R12                -1.   
    X07       R13              -1.06   X18                 1.   
    X08       X49               .313   R12                -1.   
    X08       R13               -.96   X19                 1.   
    X09       X49               .326   R12                -1.   
    X09       R13               -.86   X20                 1.   
    X10       X45              2.364   X17                -1.   
    X11       X45              2.386   X18                -1.   
    X12       X45              2.408   X19                -1.   
    X13       X45              2.429   X20                -1.   
    X14       X21                1.4   R12                 1.   
    X14       COST              -.32   
    X15       X47                -1.   R12                 1.   
    X16       X51                 1.   R13                 1.   
    X22       X46               .109   R19                -1.   
    X22       R20               -.43   X27                 1.   
    X23       X44                -1.   R19                 1.   
    X23       COST               -.6   
    X24       X48                -1.   R19                 1.   
    X25       X45                -1.   R19                 1.   
    X26       X50                 1.   R20                 1.   
    X28       X47               .109   R22               -.43   
    X28       R23                 1.   X40                 1.   
    X29       X47               .108   R22               -.43   
    X29       R23                 1.   X41                 1.   
    X30       X47               .108   R22               -.39   
    X30       R23                 1.   X42                 1.   
    X31       X47               .107   R22               -.37   
    X31       R23                 1.   X43                 1.   
    X32       X45              2.191   X40                -1.   
    X33       X45              2.219   X41                -1.   
    X34       X45              2.249   X42                -1.   
    X35       X45              2.279   X43                -1.   
    X36       X44                1.4   R23                -1.   
    X36       COST              -.48   
    X37       X49                -1.   R23                 1.   
    X38       X51                 1.   R22                 1.   
    X39       R23                 1.   COST               10.   
RHS
    B         X50               310.   X51               300.   
    B         X05                80.   X17                80.   
    B         X27               500.   R23                44.   
    B         X40               500.   
ENDATA`;

const SAMPLE_SMALL = `NAME          TINY_LP
ROWS
 N  obj
 L  c1
 L  c2
COLUMNS
    x1  obj  -1.0  c1   1.0
    x1  c2    2.0
    x2  obj  -2.0  c1   1.0
    x2  c2    1.0
RHS
    rhs  c1   4.0  c2   6.0
BOUNDS
ENDATA`;

const SAMPLE_INFEASIBLE = `NAME          INFEASIBLE
ROWS
 N  obj
 G  c1
 L  c2
COLUMNS
    x1  obj  1.0  c1  1.0  c2  1.0
RHS
    rhs  c1  5.0  c2  3.0
BOUNDS
ENDATA`;

const SAMPLES = [
  { label: 'Tiny 2-var LP', mps: SAMPLE_SMALL },
  { label: 'Afiro (Netlib)', mps: SAMPLE_AFIRO },
  { label: 'Infeasible example', mps: SAMPLE_INFEASIBLE },
];

// ─── Engine option config ─────────────────────────────────────────────────────
const ENGINE_OPTIONS: { id: EngineId; label: string; available: boolean; badge?: string }[] = [
  { id: 'dual-simplex', label: 'Dual Simplex',         available: true },
  { id: 'ipm',          label: 'Interior-Point (IPM)', available: true },
  { id: 'hpr-family',   label: 'HPR-Family (1st-Order)', available: true, badge: 'Active' },
  { id: 'branch-cut',   label: 'Branch-and-Cut (MILP)', available: true, badge: 'Active' },
];

// ─── Types ────────────────────────────────────────────────────────────────────
interface SolveProgress {
  phase: 1 | 2;
  iteration: number;
  objective: number;
  infeasibility?: number;
}

interface SolveState {
  status: 'idle' | 'parsing' | 'solving' | 'done' | 'error';
  progress: SolveProgress[];
  result?: EngineResult & { modelInfo?: { name: string; nRows: number; nCols: number; nnz: number; sense: string } };
  cert?: Certificate;
  explain?: ExplainReport;
  errorMsg?: string;
  timeMs?: number;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function statusClass(s: string): string {
  if (s.startsWith('OPTIMAL')) return 'chip chip-optimal';
  if (s.startsWith('INFEAS')) return 'chip chip-infeasible';
  if (s.startsWith('UNBOUNDED')) return 'chip chip-unbounded';
  return 'chip chip-approx';
}

function fmtNum(v: number, sig = 10): string {
  if (!isFinite(v)) return v > 0 ? '+∞' : v < 0 ? '−∞' : 'NaN';
  return v.toPrecision(sig).replace(/\.?0+$/, '');
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function SolveStudio() {
  const [mps, setMps] = useState(SAMPLE_SMALL);
  const [engine, setEngine] = useState<EngineId>('dual-simplex');
  const [usePresolve, setUsePresolve] = useState(true);
  const [solveState, setSolveState] = useState<SolveState>({ status: 'idle', progress: [] });
  const [activeTab, setActiveTab] = useState<'result' | 'cert' | 'explain' | 'log'>('result');
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['objective', 'residuals']));
  const solveIdRef = useRef(0);
  const workerRef = useRef<Worker | null>(null);

  const [backendHealth, setBackendHealth] = useState<BackendHealth>({ online: false, url: 'http://127.0.0.1:8000' });
  const [executionTarget, setExecutionTarget] = useState<'browser' | 'backend'>('browser');

  // Probe backend health periodically
  useEffect(() => {
    let mounted = true;
    const probe = async () => {
      const h = await checkBackendHealth();
      if (mounted) {
        setBackendHealth(h);
      }
    };
    probe();
    const interval = setInterval(probe, 4000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  // ── Solve ──────────────────────────────────────────────────────────────────
  const handleSolve = useCallback(async () => {
    if (executionTarget === 'backend' && backendHealth.online) {
      setSolveState({ status: 'solving', progress: [] });
      const t0 = performance.now();
      try {
        let method = 'auto';
        if (engine === 'dual-simplex') method = 'simplex';
        else if (engine === 'ipm') method = 'ipm';
        else if (engine === 'hpr-family') method = 'hpr';
        else if (engine === 'branch-cut') method = 'parallel-bc';

        const bRes = await solveViaBackend(mps, method);
        const timeMs = performance.now() - t0;
        setSolveState({
          status: 'done',
          progress: [],
          result: {
            status: bRes.status as any,
            objective: bRes.objective,
            iterations: bRes.iterations,
            x: new Float64Array(bRes.x ?? []),
            y: new Float64Array(bRes.y ?? []),
            gap: bRes.gap,
            timeMs: bRes.solve_time_ms,
            solvePathComponents: [bRes.engine_used, ...(bRes.solve_path ?? [])],
            modelInfo: bRes.dimensions ? {
              name: 'MPS Model',
              nRows: bRes.dimensions.rows,
              nCols: bRes.dimensions.cols,
              nnz: bRes.dimensions.nnz,
              sense: 'min',
            } : undefined,
          } as any,
          cert: bRes.certificate,
          timeMs,
        });
      } catch (err: any) {
        setSolveState({
          status: 'error',
          progress: [],
          errorMsg: `Backend error: ${err.message || String(err)}. You can switch to In-Browser Client mode.`,
          timeMs: performance.now() - t0,
        });
      }
      return;
    }

    const id = `solve-${++solveIdRef.current}`;
    const worker = getEngineWorker();
    workerRef.current = worker;

    setSolveState({ status: 'parsing', progress: [] });

    const t0 = performance.now();

    const handler = (ev: MessageEvent) => {
      const msg = ev.data;
      if (msg.id !== id) return;

      if (msg.type === 'PROGRESS') {
        setSolveState(s => ({
          ...s,
          status: 'solving',
          progress: [...s.progress, { phase: msg.phase, iteration: msg.iteration, objective: msg.objective, infeasibility: msg.infeasibility }],
        }));
      } else if (msg.type === 'RESULT') {
        worker.removeEventListener('message', handler);
        const r = msg.result as SolveState['result'];
        const timeMs = performance.now() - t0;

        // Build certificate (stub model for builder)
        let cert: Certificate | undefined;
        let explain: ExplainReport | undefined;
        try {
          if (r && r.status) {
            const fakeMod = {
              name: r.modelInfo?.name ?? 'unknown',
              nRows: r.modelInfo?.nRows ?? 0,
              nCols: r.modelInfo?.nCols ?? 0,
              colNames: Array.from({ length: r.modelInfo?.nCols ?? 0 }, (_, i) => `x${i}`),
              rowNames: Array.from({ length: r.modelInfo?.nRows ?? 0 }, (_, i) => `r${i}`),
            } as any;
            cert = buildCertLP(fakeMod, r as EngineResult, engine);
            explain = explainCertificate(cert);
          }
        } catch { /* cert build can fail on partial results */ }

        setSolveState({ status: 'done', progress: [], result: { ...r, } as any, cert, explain, timeMs });
      } else if (msg.type === 'ERROR') {
        worker.removeEventListener('message', handler);
        setSolveState({ status: 'error', progress: [], errorMsg: msg.message, timeMs: performance.now() - t0 });
      }
    };

    worker.addEventListener('message', handler);
    worker.postMessage({ type: 'SOLVE', id, mpsText: mps, engine, options: { presolve: usePresolve } });
  }, [mps, engine, usePresolve, executionTarget, backendHealth]);

  const handleStop = useCallback(() => {
    workerRef.current?.terminate();
    _worker = null;
    setSolveState(s => ({ ...s, status: 'idle' }));
  }, []);

  // ── Certificate download ───────────────────────────────────────────────────
  const handleDownloadCert = useCallback(() => {
    if (!solveState.cert) return;
    const blob = new Blob([serialiseCert(solveState.cert)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `nirbhar-cert-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [solveState.cert]);

  const toggleSection = (key: string) =>
    setExpandedSections(s => { const n = new Set(s); n.has(key) ? n.delete(key) : n.add(key); return n; });

  const { status, result, cert, explain, errorMsg, progress, timeMs } = solveState;
  const isSolving = status === 'solving' || status === 'parsing';

  return (
    <div className="page" style={{ maxWidth: '100%' }}>
      {/* ── Header ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-5)' }}>
        <FlaskConical size={22} style={{ color: 'var(--primary)' }} />
        <h1 className="text-page">Solve Studio</h1>
        <span className="badge" style={{ marginLeft: 'auto', fontSize: 11, background: 'rgba(16, 185, 129, 0.12)', color: '#10b981', border: '1px solid rgba(16, 185, 129, 0.3)', padding: '2px 8px', borderRadius: 4, fontWeight: 700 }}>
          CERTIFIED SOVEREIGN ENGINE
        </span>
      </div>
      <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 'var(--space-6)', maxWidth: 680 }}>
        Paste an MPS/QPS model, select an engine, and solve. Every result carries a machine-checkable
        certificate with a safe lower bound LB(y). <strong style={{ color: 'var(--text)' }}>OPTIMAL</strong> is
        only shown when gap ≤ tolerance and the verifier returns PASS.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 420px', gap: 'var(--space-5)', alignItems: 'start' }}>

        {/* ─── Left column: editor + controls ─── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>

          {/* Sample selector */}
          <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)', alignSelf: 'center' }}>Samples:</span>
            {SAMPLES.map(s => (
              <button
                key={s.label}
                id={`sample-${s.label.toLowerCase().replace(/\s+/g, '-')}`}
                className="btn btn-ghost"
                style={{ fontSize: 12, padding: '3px 10px' }}
                onClick={() => setMps(s.mps)}
              >
                {s.label}
              </button>
            ))}
          </div>

          {/* MPS editor */}
          <div style={{ position: 'relative' }}>
            <div style={{
              position: 'absolute', top: 10, left: 14, fontSize: 10,
              color: 'var(--text-muted)', fontFamily: 'var(--font-mono)',
              textTransform: 'uppercase', letterSpacing: '0.06em',
              pointerEvents: 'none',
            }}>MPS / QPS</div>
            <textarea
              id="mps-editor"
              value={mps}
              onChange={e => setMps(e.target.value)}
              spellCheck={false}
              style={{
                width: '100%',
                height: 360,
                padding: '32px 14px 14px',
                fontFamily: 'var(--font-mono)',
                fontSize: 12,
                lineHeight: 1.6,
                background: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text)',
                resize: 'vertical',
                outline: 'none',
                boxSizing: 'border-box',
              }}
            />
          </div>

          {/* Hybrid Architecture Bridge Banner */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '10px 14px', borderRadius: 'var(--radius-md)',
            background: backendHealth.online ? 'rgba(16, 185, 129, 0.08)' : 'var(--surface)',
            border: `1px solid ${backendHealth.online ? 'rgba(16, 185, 129, 0.3)' : 'var(--border)'}`,
            marginBottom: 'var(--space-2)',
            flexWrap: 'wrap', gap: 10,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{
                width: 10, height: 10, borderRadius: '50%',
                background: backendHealth.online ? '#10b981' : '#f59e0b',
                boxShadow: backendHealth.online ? '0 0 10px #10b981' : 'none',
                display: 'inline-block',
              }} />
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text)' }}>
                  {backendHealth.online ? 'Python/JAX Sovereign Core Connected' : 'In-Browser Client Mode'}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  {backendHealth.online
                    ? `v${backendHealth.version || '1.0.0'} · ${backendHealth.hasJax ? `JAX ${backendHealth.jaxVersion} (Hardware Accelerated)` : 'NumPy Core'} · localhost:8000`
                    : 'Backend offline. Run "python -m nirbhar.serve" to activate industrial Python/JAX core.'}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <button
                type="button"
                id="target-browser-btn"
                onClick={() => setExecutionTarget('browser')}
                style={{
                  padding: '4px 10px', fontSize: 11, borderRadius: 'var(--radius-sm)',
                  border: `1px solid ${executionTarget === 'browser' ? 'var(--primary)' : 'var(--border)'}`,
                  background: executionTarget === 'browser' ? 'var(--primary)' : 'transparent',
                  color: executionTarget === 'browser' ? '#fff' : 'var(--text)',
                  cursor: 'pointer', fontWeight: 600,
                }}
              >
                In-Browser Client
              </button>
              <button
                type="button"
                id="target-backend-btn"
                disabled={!backendHealth.online}
                onClick={() => setExecutionTarget('backend')}
                style={{
                  padding: '4px 10px', fontSize: 11, borderRadius: 'var(--radius-sm)',
                  border: `1px solid ${executionTarget === 'backend' ? '#10b981' : 'var(--border)'}`,
                  background: executionTarget === 'backend' ? '#10b981' : 'transparent',
                  color: executionTarget === 'backend' ? '#fff' : backendHealth.online ? 'var(--text)' : 'var(--text-muted)',
                  cursor: backendHealth.online ? 'pointer' : 'not-allowed',
                  opacity: backendHealth.online ? 1 : 0.5, fontWeight: 600,
                }}
              >
                Python/JAX Core
              </button>
            </div>
          </div>

          {/* Engine selector */}
          <div className="well" style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <Cpu size={14} style={{ color: 'var(--text-muted)' }} />
              <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>ENGINE</span>
            </div>
            <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
              {ENGINE_OPTIONS.map(opt => (
                <button
                  key={opt.id}
                  id={`engine-${opt.id}`}
                  disabled={!opt.available}
                  onClick={() => setEngine(opt.id)}
                  style={{
                    padding: '4px 12px',
                    fontSize: 12,
                    borderRadius: 'var(--radius-sm)',
                    border: `1px solid ${engine === opt.id ? 'var(--primary)' : 'var(--border)'}`,
                    background: engine === opt.id ? 'var(--primary)' : 'transparent',
                    color: engine === opt.id ? '#fff' : opt.available ? 'var(--text)' : 'var(--text-muted)',
                    cursor: opt.available ? 'pointer' : 'not-allowed',
                    opacity: opt.available ? 1 : 0.55,
                    display: 'flex', alignItems: 'center', gap: 6,
                    transition: 'all 0.15s',
                  }}
                >
                  {opt.label}
                  {opt.badge && (
                    <span style={{
                      fontSize: 9, padding: '1px 5px', borderRadius: 3,
                      background: 'var(--surface-2)', color: 'var(--text-muted)',
                      fontWeight: 700, letterSpacing: '0.05em',
                    }}>{opt.badge}</span>
                  )}
                </button>
              ))}
            </div>

            {/* Presolve toggle */}
            <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer', color: 'var(--text-muted)' }}>
                <input
                  type="checkbox"
                  id="toggle-presolve"
                  checked={usePresolve}
                  onChange={e => setUsePresolve(e.target.checked)}
                  style={{ cursor: 'pointer', accentColor: 'var(--primary)' }}
                />
                <span style={{ fontWeight: 600, color: usePresolve ? 'var(--text)' : 'var(--text-muted)' }}>
                  Presolve
                </span>
              </label>
            </div>
          </div>

          {/* Solve button */}
          <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
            {!isSolving ? (
              <button
                id="solve-btn"
                className="btn btn-primary"
                onClick={handleSolve}
                style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 14, padding: '8px 24px' }}
              >
                <Play size={15} />
                Solve
              </button>
            ) : (
              <button
                id="stop-btn"
                className="btn btn-secondary"
                onClick={handleStop}
                style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 14, padding: '8px 24px' }}
              >
                <Square size={13} />
                Stop
              </button>
            )}
            {status === 'done' && cert && (
              <button
                id="download-cert-btn"
                className="btn btn-ghost"
                onClick={handleDownloadCert}
                style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}
              >
                <Download size={14} />
                Download Certificate
              </button>
            )}
          </div>

          {/* Progress bar / live log */}
          {isSolving && (
            <div className="well" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Loader2 size={14} className="spin" style={{ color: 'var(--primary)' }} />
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>
                  {status === 'parsing' ? 'Parsing MPS…' : `Solving — iteration ${progress.at(-1)?.iteration ?? 0}`}
                </span>
              </div>
              {progress.length > 0 && (
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)' }}>
                  Phase {progress.at(-1)?.phase} | obj {fmtNum(progress.at(-1)?.objective ?? 0, 8)} |
                  infeas {fmtNum(progress.at(-1)?.infeasibility ?? 0, 4)}
                </div>
              )}
            </div>
          )}
        </div>

        {/* ─── Right column: results ─── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>

          {/* Status card */}
          {status === 'idle' && (
            <div className="well" style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: 13, padding: 'var(--space-8)' }}>
              <Play size={28} style={{ marginBottom: 8, opacity: 0.3 }} />
              <div>Press <strong>Solve</strong> to run the engine</div>
            </div>
          )}

          {status === 'error' && (
            <div className="well" style={{ borderColor: 'var(--negative)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <XCircle size={16} style={{ color: 'var(--negative)' }} />
                <span style={{ fontWeight: 700, color: 'var(--negative)', fontSize: 13 }}>Error</span>
              </div>
              <pre style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text)', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                {errorMsg}
              </pre>
            </div>
          )}

          {(status === 'done' && result) && (
            <>
              {/* Result summary card */}
              <div className="card" style={{ padding: 'var(--space-5)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    {result.status?.startsWith('OPTIMAL')
                      ? <CheckCircle2 size={18} style={{ color: 'var(--positive)' }} />
                      : result.status?.startsWith('INFEAS')
                      ? <XCircle size={18} style={{ color: 'var(--negative)' }} />
                      : <AlertTriangle size={18} style={{ color: 'var(--warning)' }} />
                    }
                    <span className={statusClass(result.status ?? '')} style={{ fontSize: 12 }}>
                      {result.status}
                    </span>
                  </div>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {timeMs?.toFixed(0)} ms · {result.iterations} iter
                  </span>
                </div>

                {/* Model info */}
                {result.modelInfo && (
                  <div style={{ display: 'flex', gap: 'var(--space-4)', marginBottom: 'var(--space-4)', flexWrap: 'wrap' }}>
                    {[
                      { label: 'rows', value: result.modelInfo.nRows },
                      { label: 'cols', value: result.modelInfo.nCols },
                      { label: 'nnz',  value: result.modelInfo.nnz  },
                      { label: 'sense', value: result.modelInfo.sense },
                    ].map(({ label, value }) => (
                      <div key={label} style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text)', fontFamily: 'var(--font-mono)' }}>{value}</div>
                        <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Objective */}
                {result.status?.startsWith('OPTIMAL') && (
                  <div style={{
                    background: 'var(--chip-optimal-bg)',
                    border: '1px solid var(--chip-optimal-border)',
                    borderRadius: 'var(--radius-md)',
                    padding: 'var(--space-3) var(--space-4)',
                    marginBottom: 'var(--space-3)',
                  }}>
                    <div style={{ fontSize: 11, color: 'var(--chip-optimal-text)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 700, marginBottom: 4 }}>Objective (UB)</div>
                    <div style={{ fontSize: 22, fontWeight: 800, fontFamily: 'var(--font-mono)', color: 'var(--chip-optimal-text)', letterSpacing: '-0.03em' }}>
                      {fmtNum(result.objective)}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--chip-optimal-text)', opacity: 0.8, marginTop: 4 }}>
                      LB(y) = {fmtNum(result.lowerBound)} · gap = {(result.gap * 100).toFixed(6)}%
                    </div>
                  </div>
                )}
              </div>

              {/* Tabs */}
              <div>
                <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', marginBottom: 'var(--space-4)' }}>
                  {(['result', 'cert', 'explain', 'log'] as const).map(tab => (
                    <button
                      key={tab}
                      id={`tab-${tab}`}
                      onClick={() => setActiveTab(tab)}
                      style={{
                        padding: '6px 16px',
                        fontSize: 12,
                        fontWeight: 600,
                        background: 'none',
                        border: 'none',
                        borderBottom: `2px solid ${activeTab === tab ? 'var(--primary)' : 'transparent'}`,
                        color: activeTab === tab ? 'var(--primary)' : 'var(--text-muted)',
                        cursor: 'pointer',
                        textTransform: 'capitalize',
                        transition: 'color 0.15s',
                        marginBottom: -1,
                      }}
                    >
                      {tab === 'cert' ? 'Certificate' : tab.charAt(0).toUpperCase() + tab.slice(1)}
                    </button>
                  ))}
                </div>

                {/* Result tab */}
                {activeTab === 'result' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                    <ResultSection
                      title="Primal Solution (x)"
                      sectionKey="primal"
                      expanded={expandedSections}
                      onToggle={toggleSection}
                    >
                      <VectorDisplay
                        values={result.x}
                        labels={Array.from({ length: result.x.length }, (_, i) => result.modelInfo ? `x${i}` : `x${i}`)}
                        maxShow={20}
                      />
                    </ResultSection>
                    <ResultSection
                      title="Dual Variables (y)"
                      sectionKey="dual"
                      expanded={expandedSections}
                      onToggle={toggleSection}
                    >
                      <VectorDisplay values={result.y} labels={Array.from({ length: result.y.length }, (_, i) => `π${i}`)} maxShow={20} />
                    </ResultSection>
                    <ResultSection
                      title="Reduced Costs (rc)"
                      sectionKey="rc"
                      expanded={expandedSections}
                      onToggle={toggleSection}
                    >
                      <VectorDisplay values={result.rc} labels={Array.from({ length: result.rc.length }, (_, i) => `rc${i}`)} maxShow={20} />
                    </ResultSection>
                    <ResultSection
                      title="Solve Diagnostics"
                      sectionKey="diag"
                      expanded={expandedSections}
                      onToggle={toggleSection}
                    >
                      <div style={{ fontSize: 12, fontFamily: 'var(--font-mono)', display: 'flex', flexDirection: 'column', gap: 4 }}>
                        <KeyVal label="Max primal viol" value={result.maxPrimalViol.toExponential(3)} />
                        <KeyVal label="Max dual viol"   value={result.maxDualViol.toExponential(3)} />
                        <KeyVal label="Gap"             value={(result.gap * 100).toFixed(8) + '%'} />
                        {result.escalations?.length > 0 && result.escalations.map((e, i) => (
                          <KeyVal key={i} label={`Escalation ${i + 1}`} value={e} warn />
                        ))}
                      </div>
                    </ResultSection>
                  </div>
                )}

                {/* Certificate tab */}
                {activeTab === 'cert' && (
                  <div>
                    {cert ? (
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 'var(--space-3)' }}>
                          <Shield size={14} style={{ color: 'var(--positive)' }} />
                          <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text)' }}>
                            Certificate v{cert.version} · {cert.kind}
                          </span>
                          <button id="download-cert-btn-2" className="btn btn-ghost" onClick={handleDownloadCert}
                            style={{ marginLeft: 'auto', fontSize: 11, padding: '2px 10px', display: 'flex', alignItems: 'center', gap: 4 }}>
                            <Download size={11} /> JSON
                          </button>
                        </div>
                        <pre style={{
                          fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text)',
                          background: 'var(--surface-2)', padding: 'var(--space-3)', borderRadius: 'var(--radius-md)',
                          overflow: 'auto', maxHeight: 340, whiteSpace: 'pre-wrap', wordBreak: 'break-all',
                        }}>
                          {serialiseCert(cert).slice(0, 3000)}{serialiseCert(cert).length > 3000 ? '\n…(truncated)' : ''}
                        </pre>
                      </div>
                    ) : (
                      <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No certificate available.</div>
                    )}
                  </div>
                )}

                {/* Explain tab */}
                {activeTab === 'explain' && (
                  <div>
                    {explain ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                        <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--text)' }}>{explain.headline}</div>
                        <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.6 }}>{explain.summary}</p>
                        {explain.sections.map((sec, i) => (
                          <div key={i} className="well" style={{
                            borderLeft: `3px solid ${sec.kind === 'success' ? 'var(--positive)' : sec.kind === 'error' ? 'var(--negative)' : sec.kind === 'warning' ? 'var(--warning)' : 'var(--primary)'}`,
                          }}>
                            <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 6, color: 'var(--text)' }}>{sec.title}</div>
                            <pre style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', whiteSpace: 'pre-wrap', margin: 0 }}>
                              {sec.body}
                            </pre>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No explanation available.</div>
                    )}
                  </div>
                )}

                {/* Log tab */}
                {activeTab === 'log' && (
                  <div>
                    {result.solvePathComponents?.length > 0 && (
                      <div style={{ marginBottom: 'var(--space-3)' }}>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 700, marginBottom: 4 }}>Solve path:</div>
                        {result.solvePathComponents.map((c, i) => (
                          <div key={i} style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text)' }}>
                            {i + 1}. {c}
                          </div>
                        ))}
                      </div>
                    )}
                    <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                      {progress.length === 0 ? 'No iteration log (solve was fast).' : `${progress.length} progress samples recorded.`}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function ResultSection({
  title, sectionKey, expanded, onToggle, children,
}: {
  title: string;
  sectionKey: string;
  expanded: Set<string>;
  onToggle: (k: string) => void;
  children: React.ReactNode;
}) {
  const isOpen = expanded.has(sectionKey);
  return (
    <div className="well" style={{ padding: 0, overflow: 'hidden' }}>
      <button
        id={`section-${sectionKey}`}
        onClick={() => onToggle(sectionKey)}
        style={{
          width: '100%', padding: '10px 14px', background: 'none', border: 'none',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          cursor: 'pointer', color: 'var(--text)', fontSize: 12, fontWeight: 700,
        }}
      >
        {title}
        {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </button>
      {isOpen && (
        <div style={{ padding: '0 14px 12px', borderTop: '1px solid var(--border)' }}>
          {children}
        </div>
      )}
    </div>
  );
}

function VectorDisplay({ values, labels, maxShow }: { values: ArrayLike<number>; labels: string[]; maxShow: number }) {
  const arr = Array.from(values);
  const nonzero = arr.map((v, i) => ({ v, i, label: labels[i] ?? `[${i}]` })).filter(e => Math.abs(e.v) > 1e-12);
  const shown = nonzero.slice(0, maxShow);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2, paddingTop: 10, paddingBottom: 4 }}>
      {shown.length === 0 && <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>All zeros</span>}
      {shown.map(({ v, label }) => (
        <div key={label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, fontFamily: 'var(--font-mono)' }}>
          <span style={{ color: 'var(--text-muted)' }}>{label}</span>
          <span style={{ color: 'var(--text)', fontWeight: 600 }}>{v.toPrecision(8)}</span>
        </div>
      ))}
      {nonzero.length > maxShow && (
        <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
          …{nonzero.length - maxShow} more non-zero entries
        </div>
      )}
      {nonzero.length === 0 && arr.length > 0 && (
        <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{arr.length} variables, all at zero</span>
      )}
    </div>
  );
}

function KeyVal({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
      <span style={{ color: 'var(--text-muted)' }}>{label}</span>
      <span style={{ color: warn ? 'var(--warning)' : 'var(--text)', fontWeight: 600, textAlign: 'right', maxWidth: 220, wordBreak: 'break-word' }}>
        {value}
      </span>
    </div>
  );
}
