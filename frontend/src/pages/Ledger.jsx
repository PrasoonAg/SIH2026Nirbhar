// pages/Ledger.jsx — Screen 8
import { useEffect, useState } from 'react'
import { useApi } from '../api/useApi.js'

const EVENT_COLORS = {
  LineUnrecognized: '#60a5fa',
  AnchorMatched:    '#818cf8',
  AdminConfirmed:   '#2dd4bf',
  GateFired:        '#fbbf24',
  GatePassed:       '#4ade80',
  GateFailed:       '#f87171',
  Rejected:         '#f87171',
  ProfileCommit:    '#4ade80',
  Demoted:          '#f97316',
  Corroborated:     '#4ade80',
  AuditCompleted:   '#60a5fa',
  ReProposed:       '#818cf8',
  SecondReviewRecorded: '#2dd4bf',
}

export default function Ledger() {
  const { api, version } = useApi()
  const [entries, setEntries] = useState([])
  const [alerts, setAlerts] = useState([])

  useEffect(() => {
    api.getLedger().then(setEntries)
    api.getAlerts().then(setAlerts)
  }, [api, version])

  const chainOk = entries.length > 0 && entries.every(e => e.chain_ok)
  const ack = async (id) => {
    await api.ackAlert(id)
    setAlerts(a => a.map(al => al.id === id ? { ...al, acknowledged: true } : al))
  }

  return (
    <div className="page fade-in">
      <h1 className="page-title">Ledger &amp; Alerts</h1>
      <p className="page-subtitle">
        Append-only SHA-256 hash-chained ledger. Every state transition carries a timestamp,
        actor, and forward link (INV-12).
      </p>

      <div className={`alert ${chainOk ? 'alert-success' : 'alert-error'} mb-3`}>
        <span>{chainOk ? '✓' : '✗'}</span>
        <div>
          <div className="fw-600">Chain integrity: {chainOk ? 'VERIFIED' : 'TAMPERED — ALERT'}</div>
          <div style={{fontSize:'.78rem'}}>
            {entries.length} entries · last hash: {entries.at(-1)?.hash}
          </div>
        </div>
      </div>

      {alerts.filter(a => !a.acknowledged).map(al => (
        <div key={al.id} className="card mb-3" style={{borderColor:'rgba(248,113,113,.3)'}}>
          <div className="flex items-center justify-between mb-1 flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <span style={{
                padding:'.1rem .4rem', borderRadius:4, fontSize:'.65rem', fontWeight:700,
                background:'rgba(248,113,113,.12)', color:'var(--sev-critical)',
              }}>{al.type}</span>
              <span className="fw-600" style={{fontSize:'.82rem'}}>{al.mapping_id}</span>
            </div>
            <button className="btn btn-ghost btn-sm" onClick={() => ack(al.id)}>Acknowledge</button>
          </div>
          <div style={{fontSize:'.8rem', color:'var(--txt-2)'}}>{al.message}</div>
          <div className="txt-3 mt-1" style={{fontSize:'.68rem'}}>{new Date(al.ts).toLocaleString()}</div>
        </div>
      ))}

      <div className="section-title">Ledger Entries ({entries.length})</div>
      <div className="card" style={{maxHeight: 520, overflow: 'auto'}}>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Event</th>
                <th>Actor</th>
                <th>Device</th>
                <th>Timestamp</th>
                <th>SHA-256</th>
                <th>Prev</th>
                <th>Chain</th>
              </tr>
            </thead>
            <tbody>
              {entries.map(e => (
                <tr key={e.seq}>
                  <td className="txt-mono txt-3">{e.seq}</td>
                  <td>
                    <span style={{ fontWeight:600, fontSize:'.78rem', color: EVENT_COLORS[e.event] || 'var(--txt)' }}>
                      {e.event}
                    </span>
                  </td>
                  <td className="txt-2" style={{fontSize:'.78rem'}}>{e.actor}</td>
                  <td className="txt-2" style={{fontSize:'.78rem'}}>{e.device}</td>
                  <td className="txt-3 txt-mono" style={{fontSize:'.68rem'}}>
                    {new Date(e.ts).toLocaleTimeString()}
                  </td>
                  <td className="txt-mono" style={{fontSize:'.62rem', color:'var(--txt-3)'}}>{e.hash}</td>
                  <td className="txt-mono" style={{fontSize:'.62rem', color:'var(--txt-3)'}}>{e.prev_hash || 'GENESIS'}</td>
                  <td>
                    {e.chain_ok
                      ? <span className="ledger-chain-ok">✓ OK</span>
                      : <span className="ledger-chain-fail">✗ FAIL</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
