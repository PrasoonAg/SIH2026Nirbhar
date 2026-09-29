// pages/FixImpact.jsx — Screen 6: Fix-Impact + Sandbox
import { useEffect, useState } from 'react'
import { TrustBadge, SeverityBadge } from '../components/Badges'
import { useApi } from '../api/useApi.js'

export default function FixImpact() {
  const { api, version } = useApi()
  const [queue, setQueue] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [activeDevice, setActiveDevice] = useState(null)
  const [isSimulating, setIsSimulating] = useState(false)
  const [simulationLog, setSimulationLog] = useState(null)

  useEffect(() => {
    api.getFixQueue().then(q => {
      setQueue(q)
      const first = q[0]
      setSelectedId(first?.check_id)
      setActiveDevice(first?.affected_devices?.[0])
    })
  }, [api, version])

  const current = queue.find(q => q.check_id === selectedId) || queue[0]
  if (!current) return <div className="page"><span className="spinner" /> Loading Fix-Impact queue…</div>

  const after = current.after_by_device?.[activeDevice] || Object.values(current.after_by_device || {})[0] || { verified: 0, provisional: 0, dependence: 0, regressions: [] }

  const handleSelectCheck = (q) => {
    setSelectedId(q.check_id)
    setActiveDevice(q.affected_devices[0])
    setSimulationLog(null)
  }

  const runSimulation = async () => {
    setIsSimulating(true)
    setSimulationLog(null)
    try {
      const log = await api.simulateFix({ checkId: current.check_id, deviceId: activeDevice })
      setSimulationLog(log)
    } finally {
      setIsSimulating(false)
    }
  }

  const diffText = current.diffs[activeDevice] || current.diffs[current.affected_devices[0]] || 'No diff available'
  const regressions = simulationLog?.regressions || []
  const noReg = simulationLog && regressions.length === 0

  return (
    <div className="page fade-in">
      <div className="flex items-center justify-between mb-1 flex-wrap gap-2">
        <h1 className="page-title">Fix-Impact Queue &amp; Simulation Sandbox</h1>
        <div className="flex items-center gap-2">
          <span className="feat-badge t2">TIER 2 (T2)</span>
          <span className="feat-badge planned">PLANNED</span>
          <span className="feat-badge planned">vision</span>
        </div>
      </div>

      <p className="page-subtitle">
        Ranked remediation queue. Impact = SeverityWeight × ExploitabilityMultiplier × FleetPrevalence.
        Simulate patches against in-memory copies (INV-09, INV-10).
      </p>

      <div className="card mb-3" style={{ background: 'rgba(26, 33, 51, 0.65)', borderLeft: '3px solid var(--accent)' }}>
        <div className="txt-mono" style={{ fontSize: '.85rem', color: 'var(--accent-teal)' }}>
          Telnet 20 × 3.0 × 0.60 = 36.0 outranking Default SNMP 20 × 2.5 × 0.20 = 10.0
        </div>
      </div>

      <div className="grid-2 gap-3" style={{ gridTemplateColumns: '1.1fr 1fr', alignItems: 'start' }}>
        <div>
          <div className="section-title">Ranked Fix-Impact Queue</div>
          {queue.map((item) => {
            const isSelected = item.check_id === selectedId
            return (
              <div
                key={item.check_id}
                onClick={() => handleSelectCheck(item)}
                className="card card-sm mb-2"
                style={{
                  cursor: 'pointer',
                  background: isSelected ? 'var(--bg-elevated)' : 'var(--bg-card)',
                  borderColor: isSelected ? 'var(--accent)' : 'var(--border)',
                }}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="fw-600" style={{
                      width: '22px', height: '22px', borderRadius: '50%',
                      background: item.rank === 1 ? 'var(--accent)' : 'var(--bg)',
                      color: item.rank === 1 ? '#fff' : 'var(--txt-2)',
                      display: 'grid', placeItems: 'center', fontSize: '.72rem',
                      fontFamily: 'var(--mono)',
                    }}>#{item.rank}</span>
                    <span className="txt-mono fw-600" style={{ fontSize: '.8rem' }}>{item.check_id}</span>
                    <SeverityBadge severity={item.severity} />
                    <TrustBadge trust={item.trust} />
                    {item.blast_radius && <span className="blast-badge">⚡ Blast Risk</span>}
                  </div>
                  <div className="txt-mono fw-600" style={{ fontSize: '1.1rem', color: 'var(--accent-teal)' }}>
                    {item.impact.toFixed(1)}
                  </div>
                </div>
                <div className="fw-600 mb-1" style={{ fontSize: '.84rem' }}>{item.title}</div>
                <div className="txt-3" style={{ fontSize: '.72rem' }}>
                  {item.severity_weight} × {item.exploitability.toFixed(1)} × {item.prevalence.toFixed(2)} = {item.impact.toFixed(1)}
                  {' · '}Fleet {item.failing_devices}/{item.total_evaluated}
                </div>
              </div>
            )
          })}
        </div>

        <div>
          <div className="section-title">Simulation Sandbox — Verified Remediation Delta</div>
          <div className="card">
            <div className="flex items-center justify-between mb-2">
              <div>
                <span className="txt-mono fw-600" style={{ fontSize: '.82rem', color: 'var(--accent)' }}>{current.check_id}</span>
                <span className="txt-3 mx-1"> · </span>
                <span className="fw-600" style={{ fontSize: '.85rem' }}>{current.title}</span>
              </div>
              <SeverityBadge severity={current.severity} />
            </div>

            {current.blast_radius && (
              <div className="alert alert-warning mb-3">
                <span>⚡</span>
                <div>
                  <div className="fw-600">Blast Radius Warning</div>
                  <div style={{ fontSize: '.75rem', marginTop: '.2rem' }}>{current.blast_note}</div>
                </div>
              </div>
            )}

            <div className="mb-3">
              <div className="form-label mb-1">Target Device:</div>
              <div className="vendor-chips">
                {current.affected_devices.map(d => (
                  <button
                    key={d}
                    onClick={() => { setActiveDevice(d); setSimulationLog(null); }}
                    className="vendor-chip"
                    style={{
                      borderColor: activeDevice === d ? 'var(--accent)' : 'var(--border)',
                      color: activeDevice === d ? 'var(--accent)' : 'var(--txt-2)',
                    }}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>

            <pre className="code-line mb-3" style={{ whiteSpace: 'pre-wrap', padding: '.75rem 1rem', fontSize: '.75rem' }}>
              {diffText.split('\n').map((line, idx) => (
                <div key={idx} style={{ color: line.startsWith('-') ? 'var(--sev-critical)' : line.startsWith('+') ? 'var(--accent-green)' : 'var(--txt-2)' }}>
                  {line}
                </div>
              ))}
            </pre>

            {simulationLog && (
              <div className="grid-2 gap-2 mb-3">
                <div className="card card-sm" style={{ background: 'var(--bg)' }}>
                  <div className="txt-3" style={{ fontSize: '.68rem' }}>Before</div>
                  <div className="stat-value" style={{ fontSize: '1.3rem' }}>{simulationLog.before_score.verified}%</div>
                  <div className="txt-3">Verified</div>
                  <div className="txt-2">{simulationLog.before_score.provisional}% Provisional-Inclusive</div>
                </div>
                <div className="card card-sm" style={{ background: 'var(--bg)', border: '1px solid rgba(74,222,128,.3)' }}>
                  <div className="txt-3" style={{ fontSize: '.68rem', color: 'var(--accent-green)' }}>After (measured)</div>
                  <div className="stat-value" style={{ fontSize: '1.3rem', color: Number(simulationLog.verified_delta) < 0 ? 'var(--sev-critical)' : 'var(--accent-green)' }}>
                    {simulationLog.after_score.verified}%
                  </div>
                  <div className="txt-3">{Number(simulationLog.verified_delta) >= 0 ? '+' : ''}{simulationLog.verified_delta} Verified</div>
                  <div className="txt-2">{simulationLog.after_score.provisional}% Provisional-Inclusive</div>
                </div>
              </div>
            )}

            {noReg && (
              <div className="alert alert-success mb-3">
                <span>✓</span>
                <div>no regressions — 0 newly failing checks on the scratch copy.</div>
              </div>
            )}
            {regressions.length > 0 && (
              <div className="alert alert-error mb-3">
                <span>✗</span>
                <div>
                  <div className="fw-600">Regression detected (measured)</div>
                  {regressions.map(rg => (
                    <div key={rg.check_id} style={{fontSize:'.78rem'}}>{rg.check_id} — {rg.title}</div>
                  ))}
                </div>
              </div>
            )}

            <button onClick={runSimulation} disabled={isSimulating} className="btn btn-primary w-full" style={{ justifyContent: 'center' }}>
              {isSimulating ? <><div className="spinner" />Re-Auditing In-Memory Scratch Copy...</> : '▶ Simulate'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
