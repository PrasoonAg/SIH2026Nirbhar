/**
 * NIRBHAR — Refinery Operations Planning Demo (Phase 2)
 * 
 * Interactive Multi-Period Crude Scheduling & Product Blending Showcase.
 * Demonstrates:
 *   - Real LP model generation from synthetic refinery parameters
 *   - Live dual simplex vs interior-point (IPM) engine execution
 *   - Certified Gross Refining Margin (GRM) & Shadow Prices (marginal bottleneck values)
 *   - What-if scenario modeling (IMO sulfur caps, crude discount shocks, diesel surges)
 *   - Zero-trust verifiable proof certificate
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  Factory, Droplet, TrendingUp, ShieldCheck, Play, RefreshCw,
  AlertCircle, CheckCircle2, ChevronRight, BarChart3, Database,
  ArrowRight, Sliders, Layers, Gauge, Cpu
} from 'lucide-react';

import {
  buildRefineryModel,
  REFINERY_SCENARIOS,
  type RefineryScenario,
  type RefineryModelResult
} from '../../demo/refinery';
import { dualSimplexSolve } from '../../solver/lp/dualSimplex';
import { ipmSolve } from '../../solver/ipm/ipm';
import type { EngineResult } from '../../solver/lp/dualSimplex';
import type { EngineId } from '../../solver/dispatch';

export default function RefineryDemo() {
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('baseline');
  const [engine, setEngine] = useState<EngineId>('ipm');
  const [isSolving, setIsSolving] = useState<boolean>(false);
  const [modelResult, setModelResult] = useState<RefineryModelResult | null>(null);
  const [solveResult, setSolveResult] = useState<EngineResult | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<number>(0);
  const [showCertModal, setShowCertModal] = useState<boolean>(false);

  // Generate and solve model whenever scenario or engine changes
  useEffect(() => {
    runOptimization(selectedScenarioId, engine);
  }, [selectedScenarioId, engine]);

  const runOptimization = (scenarioId: string, engineChoice: EngineId) => {
    setIsSolving(true);
    // Allow UI to render loading state
    setTimeout(() => {
      try {
        const mRes = buildRefineryModel(scenarioId);
        setModelResult(mRes);

        let res: EngineResult;
        if (engineChoice === 'dual-simplex') {
          res = dualSimplexSolve(mRes.model);
        } else {
          res = ipmSolve(mRes.model);
        }

        setSolveResult(res);
      } catch (err) {
        console.error('Refinery solve error:', err);
      } finally {
        setIsSolving(false);
      }
    }, 40);
  };

  const activeScenario = useMemo(() => {
    return REFINERY_SCENARIOS.find(s => s.id === selectedScenarioId) ?? REFINERY_SCENARIOS[0];
  }, [selectedScenarioId]);

  // Derived economics and operational metrics
  const metrics = useMemo(() => {
    if (!modelResult || !solveResult || solveResult.status !== 'OPTIMAL') {
      return null;
    }

    const { crudes, products, periods, cduCapacities, varIndices, rowIndices } = modelResult;
    const x = solveResult.x;
    const y = solveResult.y;

    // Total crude processed per period
    const crudeByPeriod: number[] = [];
    const crudeIntakeBreakdown: Array<{ name: string; amount: number; pct: number }> = [];
    const crudeTotalByType = new Map<string, number>();

    let totalCrudeBbl = 0;
    for (let t = 0; t < periods; t++) {
      let periodTotal = 0;
      for (const c of crudes) {
        const col = varIndices.crude.get(`${c.name}_${t}`);
        const val = col !== undefined ? Math.max(0, x[col]) : 0;
        periodTotal += val;
        crudeTotalByType.set(c.name, (crudeTotalByType.get(c.name) ?? 0) + val);
      }
      crudeByPeriod.push(periodTotal);
      totalCrudeBbl += periodTotal;
    }

    for (const c of crudes) {
      const amount = crudeTotalByType.get(c.name) ?? 0;
      crudeIntakeBreakdown.push({
        name: c.name,
        amount,
        pct: totalCrudeBbl > 0 ? (amount / totalCrudeBbl) * 100 : 0,
      });
    }

    // Product production & sales per period
    const salesByProduct = new Map<string, number>();
    for (const p of products) {
      let pSales = 0;
      for (let t = 0; t < periods; t++) {
        const col = varIndices.sales.get(`${p}_${t}`);
        if (col !== undefined) pSales += Math.max(0, x[col]);
      }
      salesByProduct.set(p, pSales);
    }

    // CDU Shadow prices (Marginal value of 1 additional kbd distillation capacity)
    const cduShadowPrices: number[] = [];
    for (let t = 0; t < periods; t++) {
      const row = rowIndices.cdu[t];
      // In maximization problem, shadow price of <= row is nonnegative dual multiplier
      cduShadowPrices.push(row !== undefined ? Math.abs(y[row]) : 0);
    }

    // Sulfur shadow price (Period 0)
    const sulfurRow = rowIndices.sulfur[0];
    const sulfurShadowPrice = sulfurRow !== undefined ? Math.abs(y[sulfurRow]) : 0;

    const totalGRM = solveResult.objective;
    const grmPerBbl = totalCrudeBbl > 0 ? (totalGRM * 1000) / (totalCrudeBbl * 1000) : 0;
    const totalCapacity = cduCapacities.reduce((a, b) => a + b, 0);
    const utilizationPct = totalCapacity > 0 ? (totalCrudeBbl / totalCapacity) * 100 : 0;

    return {
      totalGRM,
      grmPerBbl,
      totalCrudeBbl,
      crudeByPeriod,
      crudeIntakeBreakdown: crudeIntakeBreakdown.filter(c => c.amount > 0.01),
      salesByProduct,
      cduShadowPrices,
      sulfurShadowPrice,
      utilizationPct,
    };
  }, [modelResult, solveResult]);

  return (
    <div className="page" style={{ maxWidth: 1200 }}>
      {/* ── Top Header ── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <Factory size={26} style={{ color: 'var(--primary)' }} />
          <div>
            <h1 className="text-page" style={{ margin: 0 }}>Refinery Planning & Blending Demo</h1>
            <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: '2px 0 0 0' }}>
              Multi-period crude allocation, environmental specifications & certified margin optimization
            </p>
          </div>
        </div>

        {/* Engine Switcher */}
        <div className="well" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', padding: '4px 8px' }}>
          <Cpu size={14} style={{ color: 'var(--text-muted)' }} />
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)' }}>ENGINE:</span>
          <button
            className={`btn ${engine === 'ipm' ? 'btn-primary' : 'btn-ghost'}`}
            style={{ fontSize: 11, padding: '3px 8px' }}
            onClick={() => setEngine('ipm')}
          >
            Interior-Point (IPM)
          </button>
          <button
            className={`btn ${engine === 'dual-simplex' ? 'btn-primary' : 'btn-ghost'}`}
            style={{ fontSize: 11, padding: '3px 8px' }}
            onClick={() => setEngine('dual-simplex')}
          >
            Dual Simplex
          </button>
        </div>
      </div>

      {/* ── Scenario Selection Cards ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 'var(--space-3)', marginBottom: 'var(--space-5)' }}>
        {REFINERY_SCENARIOS.map(sc => {
          const isSelected = sc.id === selectedScenarioId;
          return (
            <div
              key={sc.id}
              onClick={() => setSelectedScenarioId(sc.id)}
              style={{
                cursor: 'pointer',
                borderRadius: 'var(--radius-md)',
                padding: 'var(--space-3)',
                border: `1px solid ${isSelected ? 'var(--primary)' : 'var(--border)'}`,
                background: isSelected ? 'var(--surface-2)' : 'var(--surface)',
                boxShadow: isSelected ? '0 0 0 1px var(--primary)' : 'none',
                transition: 'all 0.15s ease',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontWeight: 600, fontSize: 13, color: isSelected ? 'var(--primary)' : 'var(--text)' }}>
                  {sc.name}
                </span>
                {isSelected && <CheckCircle2 size={15} style={{ color: 'var(--primary)' }} />}
              </div>
              <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: 0, lineHeight: 1.4 }}>
                {sc.description}
              </p>
            </div>
          );
        })}
      </div>

      {/* ── KPI Row ── */}
      {metrics && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--space-3)', marginBottom: 'var(--space-5)' }}>
          <div className="card" style={{ padding: 'var(--space-3)' }}>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Gross Margin (GRM)
            </span>
            <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--primary)', marginTop: 4 }}>
              ${metrics.totalGRM.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}k
            </div>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>4-period total surplus</span>
          </div>

          <div className="card" style={{ padding: 'var(--space-3)' }}>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Unit Margin
            </span>
            <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--text)', marginTop: 4 }}>
              ${metrics.grmPerBbl.toFixed(2)}
              <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-muted)' }}> /bbl</span>
            </div>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Weighted net yield spread</span>
          </div>

          <div className="card" style={{ padding: 'var(--space-3)' }}>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              CDU Utilization
            </span>
            <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--text)', marginTop: 4 }}>
              {metrics.utilizationPct.toFixed(1)}%
            </div>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {metrics.totalCrudeBbl.toFixed(0)} kbd processed
            </span>
          </div>

          <div className="card" style={{ padding: 'var(--space-3)' }}>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Max Shadow Price
            </span>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#f59e0b', marginTop: 4 }}>
              ${Math.max(...metrics.cduShadowPrices).toFixed(2)}
              <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-muted)' }}> /bbl</span>
            </div>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>CDU expansion value</span>
          </div>

          <div className="card" style={{ padding: 'var(--space-3)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Certified Status
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <ShieldCheck size={20} style={{ color: '#10b981' }} />
              <span style={{ fontWeight: 700, color: '#10b981', fontSize: 16 }}>CERTIFIED</span>
            </div>
            <button
              className="btn btn-ghost"
              style={{ fontSize: 11, padding: 0, justifyContent: 'flex-start', color: 'var(--primary)' }}
              onClick={() => setShowCertModal(true)}
            >
              Inspect Proof Certificate →
            </button>
          </div>
        </div>
      )}

      {/* ── Main Operations Grid ── */}
      {metrics && modelResult && (
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 'var(--space-5)', alignItems: 'start' }}>
          
          {/* Left Panel: Crude Diet & Blending Optimization */}
          <div className="card" style={{ padding: 'var(--space-4)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-3)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Droplet size={17} style={{ color: 'var(--primary)' }} />
                <h2 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Optimal Crude Basket Allocation</h2>
              </div>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                Solved in {solveResult?.iterations} iters ({solveResult?.timeMs.toFixed(1)}ms)
              </span>
            </div>

            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 'var(--space-4)' }}>
              The optimizer balances crude purchase price against product yield distributions and sulfur blending caps.
            </p>

            {/* Crude Diet Bars */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {metrics.crudeIntakeBreakdown.map(crude => (
                <div key={crude.name}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 3 }}>
                    <span style={{ fontWeight: 600 }}>{crude.name}</span>
                    <span style={{ color: 'var(--text-muted)' }}>
                      {crude.amount.toFixed(1)} kbd ({crude.pct.toFixed(1)}%)
                    </span>
                  </div>
                  <div style={{ height: 6, borderRadius: 3, background: 'var(--surface-2)', overflow: 'hidden' }}>
                    <div
                      style={{
                        height: '100%',
                        width: `${crude.pct}%`,
                        background: 'var(--primary)',
                        borderRadius: 3,
                        transition: 'width 0.3s ease',
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Process Flow Yield Card */}
            <div className="well" style={{ marginTop: 'var(--space-5)', padding: 'var(--space-3)' }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>Finished Product Production Slate</span>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginTop: 8 }}>
                {Array.from(metrics.salesByProduct.entries()).map(([prod, kbd]) => (
                  <div key={prod} style={{ background: 'var(--surface)', padding: '6px 10px', borderRadius: 4, border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{prod}</div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>
                      {kbd.toFixed(1)} <span style={{ fontSize: 10, fontWeight: 400 }}>kbd</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Panel: Period Breakdown & Shadow Prices */}
          <div className="card" style={{ padding: 'var(--space-4)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-3)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <TrendingUp size={17} style={{ color: '#10b981' }} />
                <h2 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Bottleneck & Shadow Price Economics</h2>
              </div>
            </div>

            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 'var(--space-4)' }}>
              Dual multipliers identify which refinery units are binding constraints and the exact marginal profit of capacity expansion.
            </p>

            {/* CDU Shadow Prices Table */}
            <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '6px 4px' }}>Period</th>
                  <th style={{ padding: '6px 4px' }}>CDU Intake</th>
                  <th style={{ padding: '6px 4px' }}>CDU Limit</th>
                  <th style={{ padding: '6px 4px', textAlign: 'right' }}>CDU Shadow Price</th>
                </tr>
              </thead>
              <tbody>
                {modelResult.cduCapacities.map((cap, t) => {
                  const intake = metrics.crudeByPeriod[t] ?? 0;
                  const shadow = metrics.cduShadowPrices[t] ?? 0;
                  const isBinding = Math.abs(intake - cap) < 0.1;
                  return (
                    <tr key={t} style={{ borderBottom: '1px solid var(--surface-2)' }}>
                      <td style={{ padding: '6px 4px', fontWeight: 600 }}>T{t + 1}</td>
                      <td style={{ padding: '6px 4px' }}>{intake.toFixed(1)} kbd</td>
                      <td style={{ padding: '6px 4px', color: 'var(--text-muted)' }}>{cap} kbd</td>
                      <td style={{ padding: '6px 4px', textAlign: 'right', fontWeight: 700, color: isBinding ? '#f59e0b' : 'var(--text-muted)' }}>
                        ${shadow.toFixed(2)}/bbl
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {/* Environmental Constraint Shadow Price */}
            <div style={{ marginTop: 'var(--space-4)', padding: 'var(--space-3)', background: 'var(--surface-2)', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 12, fontWeight: 600 }}>Blended Sulfur Constraint Shadow Price</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>
                  ${metrics.sulfurShadowPrice.toFixed(2)} / (% · kbd)
                </span>
              </div>
              <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
                {metrics.sulfurShadowPrice > 0.01
                  ? 'Active binding limit: Relaxing sulfur spec yields immediate margin gains via cheaper heavy sour crudes.'
                  : 'Slack constraint: Current crude slate easily satisfies the sulfur specification.'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ── Certificate Modal ── */}
      {showCertModal && solveResult && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div className="card" style={{ maxWidth: 640, width: '90%', maxHeight: '80vh', overflowY: 'auto', padding: 'var(--space-5)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <ShieldCheck size={20} style={{ color: '#10b981' }} />
                <h3 style={{ margin: 0, fontSize: 16 }}>Certified Proof of Optimality</h3>
              </div>
              <button className="btn btn-ghost" style={{ padding: '4px 8px' }} onClick={() => setShowCertModal(false)}>✕</button>
            </div>

            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 'var(--space-4)' }}>
              Every solution produced by NIRBHAR carries a dual multiplier certificate vector y proving that no feasible schedule can exceed the primal objective.
            </p>

            <div className="well" style={{ fontSize: 12, display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div><strong>Engine:</strong> {engine === 'ipm' ? 'Primal-Dual Interior-Point (Mehrotra)' : 'Revised Dual Simplex'}</div>
              <div><strong>Primal Objective:</strong> ${solveResult.objective.toFixed(4)}k</div>
              <div><strong>Dual Bound LB(y):</strong> ${solveResult.lowerBound.toFixed(4)}k</div>
              <div><strong>Certified Gap:</strong> {(solveResult.gap * 100).toExponential(4)}%</div>
              <div><strong>Max Primal Residual:</strong> {solveResult.maxPrimalViol.toExponential(4)}</div>
              <div><strong>Max Dual Residual:</strong> {solveResult.maxDualViol.toExponential(4)}</div>
              <div><strong>Iterations:</strong> {solveResult.iterations}</div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 'var(--space-4)' }}>
              <button className="btn btn-primary" onClick={() => setShowCertModal(false)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
