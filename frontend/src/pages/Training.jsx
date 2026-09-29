// pages/Training.jsx — Screen 3: Training Studio (§11)
import { useState, useEffect } from 'react'
import { StateNode } from '../components/Badges'
import { useApi } from '../api/useApi.js'

const VENDOR_LABELS = {
  cisco_ios: 'Cisco IOS', juniper_junos: 'JunOS',
  palo_alto_panos: 'PAN-OS', fortinet_fortios: 'FortiOS',
}

function Artifact({ artifact }) {
  if (!artifact) return null
  if (artifact.type === 'hex-diff') {
    return (
      <pre className="code-line" style={{ whiteSpace: 'pre-wrap', fontSize: '.68rem', marginTop: '.35rem' }}>
        {artifact.snippet}
      </pre>
    )
  }
  if (artifact.type === 'bm25') {
    return (
      <div className="table-wrap mt-1">
        <table>
          <thead><tr><th>Rank</th><th>Setting</th><th>BM25</th></tr></thead>
          <tbody>
            {(artifact.rows || []).map(r => (
              <tr key={r.rank}>
                <td className="txt-mono">{r.rank}</td>
                <td className="txt-mono" style={{fontSize:'.7rem'}}>{r.setting_id}</td>
                <td className="txt-mono">{r.score.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }
  if (artifact.type === 'ranker') {
    return (
      <div className="txt-3 mt-1" style={{fontSize:'.72rem'}}>
        Ranker score <strong className="txt-mono" style={{color:'var(--txt)'}}>{artifact.score}</strong> · rank {artifact.rank}
      </div>
    )
  }
  return null
}

function GatePanel({ verdict }) {
  const checks = [
    { name: 'RegenCheck', desc: 'spec.match(line) → render → match must round-trip byte-for-byte', data: verdict?.regen },
    { name: 'LexicalCheck', desc: 'BM25 — proposed target must rank ≤ top_k and score ≥ min_score', data: verdict?.lexical },
    { name: 'SecondModelCheck', desc: 'Verifier (different family) — proposed target must be rank-1', data: verdict?.second_model },
  ]
  const outcome = verdict?.outcome
  return (
    <div className="card" style={{marginTop:'1rem'}}>
      <div className="section-title">Trust Gate — 3 Checks (§6.3)</div>
      {checks.map(c => {
        const v = c.data?.verdict
        return (
          <div key={c.name} className="mb-3">
            <div className="flex items-center gap-2" style={{flexWrap:'wrap'}}>
              <span className={`finding-status-icon ${v === 'PASS' ? 'pass' : v === 'FAIL' ? 'fail' : 'unevaluated'}`}
                style={{width:22,height:22,fontSize:'.68rem'}}>
                {v === 'PASS' ? '✓' : v === 'FAIL' ? '✗' : '?'}
              </span>
              <div style={{flex:1}}>
                <div className="fw-600" style={{fontSize:'.8rem'}}>{c.name}</div>
                <div className="txt-3" style={{fontSize:'.7rem'}}>{c.desc}</div>
                {c.data?.detail && <div className="txt-2" style={{fontSize:'.72rem'}}>{c.data.detail}</div>}
              </div>
              {v && (
                <span style={{
                  padding:'.1rem .45rem', borderRadius:4, fontSize:'.65rem', fontWeight:700,
                  background: v === 'PASS' ? 'rgba(74,222,128,.1)' : 'rgba(248,113,113,.1)',
                  color: v === 'PASS' ? 'var(--accent-green)' : 'var(--sev-critical)',
                }}>{v}</span>
              )}
            </div>
            <Artifact artifact={c.data?.artifact} />
          </div>
        )
      })}
      {outcome && (
        <div className={`alert ${outcome === 'PASSED' ? 'alert-success' : 'alert-error'} mt-1`}>
          <span>{outcome === 'PASSED' ? '✓' : '✗'}</span>
          <span>Gate outcome: <strong>{outcome}</strong> — mapping transitions to {outcome === 'PASSED' ? 'Provisional' : 'Rejected'}</span>
        </div>
      )}
    </div>
  )
}

export default function Training() {
  const { api, version } = useApi()
  const [queue, setQueue] = useState([])
  const [taxonomy, setTaxonomy] = useState([])
  const [active, setActive] = useState(null)
  const [target, setTarget] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [matching, setMatching] = useState(false)
  const [gate, setGate] = useState(null)
  const [mappingState, setMappingState] = useState(null)

  useEffect(() => {
    api.getTrainingQueue().then(q => {
      setQueue(q)
      setActive(cur => cur ? q.find(x => x.id === cur.id) || q[0] : q[0])
    })
    api.getTaxonomy().then(setTaxonomy)
  }, [api, version])

  const openSig = async (sig) => {
    setGate(null)
    setMappingState(null)
    setMatching(true)
    setActive(sig)
    setTarget(sig.candidates?.[0]?.setting_id || '')
    try {
      const matched = await api.matchAnchors(sig.id)
      setActive(matched)
      setTarget(matched.candidates?.[0]?.setting_id || '')
    } finally {
      setMatching(false)
    }
  }

  const handleConfirm = async () => {
    if (!active) return
    setSubmitting(true)
    setGate(null)
    try {
      const chosen = target || active.candidates[0].setting_id
      const res = await api.submitMapping({ signatureId: active.id, target: chosen, actor: 'alice' })
      setGate(res.gate)
      setMappingState(res.state)
      const q = await api.getTrainingQueue()
      setQueue(q)
      setActive(q.find(x => x.id === active.id) || q[0])
    } finally {
      setSubmitting(false)
    }
  }

  const loadWrongControl = () => {
    const sig = queue.find(s => s.demo_fixture === 'wrong-control' || s.id === 'sig-wrong-control')
    if (sig) openSig(sig)
  }

  return (
    <div className="page fade-in">
      <div className="flex items-center justify-between mb-1 flex-wrap gap-2">
        <h1 className="page-title">Training Studio</h1>
        <button className="btn btn-secondary btn-sm" onClick={loadWrongControl} id="demo-beat-3">
          Demo beat 3 — wrong-control fixture
        </button>
      </div>
      <p className="page-subtitle">
        Review AI-proposed mappings for unrecognized config lines.
        Confirm or correct — then the Trust Gate runs RegenCheck, LexicalCheck and SecondModelCheck.
      </p>

      <div style={{display:'grid', gridTemplateColumns:'300px 1fr', gap:'1.5rem'}}>
        <div>
          <div className="section-title">Unrecognized Queue ({queue.length})</div>
          {queue.map(sig => (
            <div key={sig.id}
              className="card card-sm mb-2"
              style={{cursor:'pointer', borderColor: active?.id === sig.id ? 'var(--accent)' : 'var(--border)', transition:'all .15s'}}
              onClick={() => openSig(sig)}>
              <div className="flex items-center justify-between mb-1">
                <StateNode state={sig.state} />
                <span className="txt-3" style={{fontSize:'.68rem'}}>{sig.occurrences}×</span>
              </div>
              <div className="code-line" style={{marginTop:'.4rem', fontSize:'.7rem', overflow:'hidden', whiteSpace:'nowrap', textOverflow:'ellipsis'}}>
                {sig.redacted_line}
              </div>
              <div className="txt-3 mt-1" style={{fontSize:'.65rem'}}>
                {VENDOR_LABELS[sig.vendor_id]} · {sig.dialect_fingerprint}
                {sig.demo_fixture === 'wrong-control' && <span style={{marginLeft:'.35rem', color:'var(--sev-high)'}}>fixture</span>}
              </div>
            </div>
          ))}
        </div>

        {active && (
          <div className="fade-in">
            <div className="card mb-2">
              <div className="section-title">Unrecognized Line</div>
              <div className="code-line mb-2">{active.redacted_line}</div>
              <div className="flex gap-2 flex-wrap txt-3" style={{fontSize:'.72rem'}}>
                <span>Vendor: <strong style={{color:'var(--txt)'}}>{VENDOR_LABELS[active.vendor_id]}</strong></span>
                <span>Device: <strong style={{color:'var(--txt)'}}>{active.device_id}</strong></span>
                <span>Fingerprint: <span className="txt-mono">{active.dialect_fingerprint}</span></span>
              </div>
              {matching && <div className="mt-2"><span className="spinner" /> Embedding match…</div>}
            </div>

            <div className="card mb-2">
              <div className="section-title">Top-3 Anchor Candidates</div>
              {(active.candidates || []).map((c, i) => (
                <div key={c.setting_id} className="mb-2">
                  <div className="cosine-bar">
                    <div className="cosine-label">
                      <div className="fw-600" style={{fontSize:'.78rem'}}>{c.setting_id}</div>
                      <div className="txt-3" style={{fontSize:'.7rem'}}>{c.phrase}</div>
                    </div>
                    <div className="cosine-track">
                      <div className="cosine-fill" style={{width:`${c.cosine * 100}%`}} />
                    </div>
                    <div className="cosine-val">{c.cosine.toFixed(2)}</div>
                  </div>
                  {i === 0 && (
                    <div style={{marginTop:'.25rem', paddingLeft:'192px'}}>
                      <span style={{fontSize:'.6rem', background:'rgba(59,130,246,.1)', color:'var(--accent)',
                        padding:'.1rem .4rem', borderRadius:4}}>Top-1 proposal</span>
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="card mb-2">
              <div className="section-title">Target Setting</div>
              <div className="form-group mb-2">
                <label className="form-label">Select target from taxonomy or accept top-1</label>
                <select className="input select"
                  value={target || active.candidates?.[0]?.setting_id || ''}
                  onChange={e => setTarget(e.target.value)}>
                  {taxonomy.map(o => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>

              <div className="section-title" style={{marginTop:'.75rem'}}>Regen Diff Preview</div>
              <div className="code-line" style={{color:'var(--accent-green)', whiteSpace:'pre-wrap'}}>
                {`  ${active.redacted_line}\n+ render(spec, match(spec, line)) == line`}
              </div>

              <div className="flex gap-2 mt-2">
                <button className="btn btn-primary" disabled={submitting || matching}
                  onClick={handleConfirm}>
                  {submitting ? <><span className="spinner"/>Running gate…</> : '✓ Confirm & Submit to Gate'}
                </button>
              </div>
            </div>

            {gate && <GatePanel verdict={gate} />}
            {mappingState === 'Rejected' && (
              <div className="alert alert-error mt-2">
                <span>🚫</span>
                <div>
                  <div className="fw-600">Rejected — absorbing (INV-01)</div>
                  <div style={{fontSize:'.78rem'}}>No override control. Open the Mapping page to Re-propose from scratch.</div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
