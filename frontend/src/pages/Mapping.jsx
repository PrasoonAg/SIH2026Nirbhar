// pages/Mapping.jsx — Screen 4: Mapping Page (§11)
import { useState, useEffect } from 'react'
import { StateNode } from '../components/Badges'
import MappingFlow from '../components/MappingFlow'
import { useApi } from '../api/useApi.js'

function GateReport({ run }) {
  const checks = [
    { name: 'RegenCheck', key: 'regen' },
    { name: 'LexicalCheck', key: 'lexical' },
    { name: 'SecondModelCheck', key: 'second_model' },
  ]
  return (
    <div className="card mb-2">
      <div className="flex items-center justify-between mb-2">
        <div className="fw-600" style={{fontSize:'.85rem'}}>Gate Report — {run.gate_run_id || run.id}</div>
        <span style={{
          padding:'.15rem .55rem', borderRadius:4, fontSize:'.65rem', fontWeight:700,
          background: run.outcome === 'PASSED' ? 'rgba(74,222,128,.1)' : 'rgba(248,113,113,.1)',
          color: run.outcome === 'PASSED' ? 'var(--accent-green)' : 'var(--sev-critical)',
        }}>{run.outcome}</span>
      </div>
      {checks.map(c => {
        const ch = run[c.key] || {}
        return (
          <div key={c.key} className="flex items-start gap-2 mb-2">
            <span className={`finding-status-icon ${ch.verdict === 'PASS' ? 'pass' : 'fail'}`}
              style={{width:20,height:20,fontSize:'.62rem',flexShrink:0}}>
              {ch.verdict === 'PASS' ? '✓' : '✗'}
            </span>
            <div>
              <div className="fw-600" style={{fontSize:'.78rem'}}>{c.name}</div>
              <div className="txt-3" style={{fontSize:'.72rem'}}>{ch.detail}</div>
            </div>
          </div>
        )
      })}
      <div className="txt-3" style={{fontSize:'.65rem', marginTop:'.5rem'}}>
        Run at: {run.run_at ? new Date(run.run_at).toLocaleString() : '—'}
      </div>
    </div>
  )
}

export default function Mapping() {
  const { api, version } = useApi()
  const [list, setList] = useState([])
  const [selected, setSelected] = useState(null)
  const [reviewInput, setReviewInput] = useState('')
  const [taxonomy, setTaxonomy] = useState([])
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.getMappings().then(rows => {
      setList(rows)
      setSelected(cur => {
        if (cur) return rows.find(x => x.id === cur.id) || rows[0]
        return rows[0]
      })
    })
    api.getTaxonomy().then(setTaxonomy)
  }, [api, version])

  const isRejected = selected?.state === 'Rejected'

  const submitReview = async () => {
    if (!selected || !reviewInput) return
    setBusy(true)
    try {
      const updated = await api.secondReview({ mappingId: selected.id, choice: reviewInput, actor: 'reviewer-2' })
      setSelected(updated)
      setReviewInput('')
    } finally {
      setBusy(false)
    }
  }

  const repropose = async () => {
    if (!selected) return
    setBusy(true)
    try {
      await api.repropose(selected.id)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page fade-in">
      <h1 className="page-title">Mapping Lifecycle</h1>
      <p className="page-subtitle">
        Unmapped → Proposed → AdminReviewed → Gating → Provisional/Rejected → ReVerification → Corroborated/Demoted.
        Evidence ledger · Blind second-reviewer · INV-01 absorbing Rejected.
      </p>

      <div style={{display:'grid', gridTemplateColumns:'300px 1fr', gap:'1.5rem'}}>
        <div>
          <div className="section-title">Mappings ({list.length})</div>
          {list.map(m => (
            <div key={m.id}
              className="card card-sm mb-2"
              style={{cursor:'pointer', borderColor: selected?.id === m.id ? 'var(--accent)' : 'var(--border)', transition:'all .15s'}}
              onClick={() => { setSelected(m); setReviewInput('') }}>
              <div className="flex items-center justify-between mb-1">
                <StateNode state={m.state} />
                <span className="txt-mono txt-3" style={{fontSize:'.62rem'}}>{m.id}</span>
              </div>
              <div className="code-line" style={{fontSize:'.68rem', marginTop:'.35rem', overflow:'hidden', whiteSpace:'nowrap', textOverflow:'ellipsis'}}>
                {m.redacted_line}
              </div>
              <div className="txt-3 mt-1" style={{fontSize:'.65rem'}}>
                {m.state === 'Rejected' || !m.blind_pending ? `→ ${m.target_setting}` : 'target hidden (blind review)'}
              </div>
            </div>
          ))}
        </div>

        {selected && (
          <div className="fade-in">
            <div className="card mb-3">
              <div className="section-title">Trust Lifecycle</div>
              <MappingFlow currentState={selected.state} />
            </div>

            {selected.state === 'Rejected' && (
              <div className="alert alert-error mb-3">
                <span>🚫</span>
                <div>
                  <div className="fw-600 mb-1">Rejected — absorbing state (INV-01)</div>
                  <div style={{fontSize:'.78rem'}}>No API, flag, role or CLI command can move this mapping out of Rejected.
                    Create a new proposal with a <code>supersedes</code> link.</div>
                </div>
              </div>
            )}

            <div className="card mb-3">
              <div className="section-title">Mapping Detail</div>
              <div className="grid-2 mb-2" style={{gap:'.75rem'}}>
                {[
                  ['ID', selected.id],
                  ['State', <StateNode state={selected.state} />],
                  ['Target', selected.blind_pending && selected.state !== 'Rejected'
                    ? <span className="txt-3">hidden until second reviewer submits</span>
                    : <code className="txt-mono" style={{color:'var(--accent-teal)'}}>{selected.target_setting}</code>],
                  ['Proposer', selected.proposer_card || '—'],
                  ['Top-1 Cosine', selected.top1_cosine?.toFixed(2) || '—'],
                  ['Profile Commit', selected.profile_commit || '—'],
                ].map(([k, v]) => (
                  <div key={k}>
                    <div className="txt-3" style={{fontSize:'.68rem', marginBottom:'.2rem'}}>{k}</div>
                    <div style={{fontSize:'.82rem', fontWeight:500}}>{v}</div>
                  </div>
                ))}
              </div>
              <div className="txt-3" style={{fontSize:'.72rem'}}>Redacted line:</div>
              <div className="code-line mt-1">{selected.redacted_line}</div>
            </div>

            <div className="section-title">Gate Reports</div>
            {(selected.gate_runs || []).map(run => <GateReport key={run.gate_run_id || run.id} run={run} />)}

            <div className="section-title">Evidence Ledger</div>
            <div className="card mb-3">
              {(selected.evidence || []).length === 0 && <div className="txt-3">No evidence items (Rejected mappings carry none).</div>}
              {(selected.evidence || []).map(e => (
                <div key={e.id} className="ledger-entry">
                  <div className="ledger-seq">{e.cls}</div>
                  <div className="flex-col" style={{flex:1}}>
                    <div className="ledger-event">weight {e.weight}</div>
                    <div className="ledger-actor">actor: {e.actor} · {e.reason}</div>
                  </div>
                </div>
              ))}
            </div>

            {!isRejected && selected.blind_pending && (
              <div className="card mb-3">
                <div className="section-title">Blind Second Reviewer (§6.4)</div>
                <div className="alert alert-info mb-2">
                  <span>ℹ</span>
                  <span>The first admin&apos;s choice is hidden until you submit your review (blind review protocol).</span>
                </div>
                <div className="form-group mb-2">
                  <label className="form-label">Your assessment of: <code className="txt-mono">{selected.redacted_line}</code></label>
                  <select className="input select" value={reviewInput} onChange={e => setReviewInput(e.target.value)}>
                    <option value="">Select target setting…</option>
                    {taxonomy.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <button className="btn btn-primary btn-sm" disabled={!reviewInput || busy} onClick={submitReview}>
                  {busy ? <><span className="spinner" />Submitting…</> : 'Submit Review'}
                </button>
                <div className="txt-3 mt-1" style={{fontSize:'.7rem'}}>
                  Agreement → weight 1 (corroboration). Disagreement → weight 0, recorded, blocks upgrade until resolved. Same actor → weight 0 (INV-06).
                </div>
              </div>
            )}

            {selected.second_review && !selected.blind_pending && (
              <div className={`alert ${selected.state === 'Corroborated' ? 'alert-success' : 'alert-info'} mb-3`}>
                <span>✓</span>
                <div>
                  <div className="fw-600">Review submitted</div>
                  <div style={{fontSize:'.78rem'}}>
                    First admin chose <code>{selected.first_admin_choice}</code>. Weight = {selected.second_review.weight}.
                    State: {selected.state}.
                  </div>
                </div>
              </div>
            )}

            {isRejected && (
              <div className="card mb-3">
                <div className="section-title" style={{color:'var(--sev-critical)'}}>Rejected — No Override</div>
                <div className="alert alert-error mb-2">
                  <span>🚫</span>
                  <span>INV-01: Rejected is absorbing. No override is available through any API, role, or CLI path.</span>
                </div>
                <button className="btn btn-secondary btn-sm" disabled={busy} onClick={repropose}>
                  Re-propose from scratch
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
