// pages/SelfAudit.jsx — Screen 5: Self-Audit (§11, §13)
import { useEffect, useState } from 'react'
import { useApi } from '../api/useApi.js'

function RateCard({ label, n, rate, ci, total, note }) {
  const pct = (rate * 100).toFixed(1)
  const ciLo = (ci[0] * 100).toFixed(1)
  const ciHi = (ci[1] * 100).toFixed(1)
  const color = rate === 0 ? 'var(--accent-green)' : rate < 0.02 ? 'var(--accent-amber)' : 'var(--sev-critical)'

  return (
    <div className="rate-card">
      <div className="rate-label">{label}</div>
      <div className="rate-num" style={{color}}>{pct}%</div>
      <div className="rate-interval">{n}/{total} · 95% Wilson CI [{ciLo}%, {ciHi}%]</div>
      {note && <div className="txt-3 mt-1" style={{fontSize:'.68rem'}}>{note}</div>}
    </div>
  )
}

export default function SelfAudit() {
  const { api, version } = useApi()
  const [r, setR] = useState(null)

  useEffect(() => {
    api.getSelfAudit().then(setR)
  }, [api, version])

  if (!r) return <div className="page"><span className="spinner" /> Loading self-audit…</div>

  const stages = [
    { key: 'regen',        label: 'RegenCheck' },
    { key: 'lexical',      label: 'LexicalCheck' },
    { key: 'second_model', label: 'SecondModelCheck' },
    { key: 'overall',      label: 'Overall (AND)' },
  ]

  return (
    <div className="page fade-in">
      <h1 className="page-title">Self-Audit</h1>
      <p className="page-subtitle">
        Measured false-accept and false-reject rates with Wilson 95% confidence intervals.
        Run: <code className="txt-mono">pramana selfaudit --seed {r.seed}</code> · INV-15
      </p>

      <div className="card mb-3">
        <div className="section-title">Audit Metadata</div>
        <div className="grid-3 mb-2" style={{gap:'.75rem'}}>
          {[
            ['Seed',              String(r.seed)],
            ['Corpus SHA-256',    r.corpus_sha256],
            ['Gate Config Hash',  r.gate_config_hash],
            ['Generated At',      new Date(r.generated_at).toLocaleString()],
            ['Corpus Size',       '140 line-setting pairs'],
            ['Hard Negatives',    '20 (BM25 + cosine nearest)'],
          ].map(([k, v]) => (
            <div key={k}>
              <div className="txt-3" style={{fontSize:'.68rem'}}>{k}</div>
              <div className="txt-mono fw-600" style={{fontSize:'.72rem', wordBreak:'break-all'}}>{v}</div>
            </div>
          ))}
        </div>

        <div className="section-title">Model Cards (INV-17)</div>
        <div className="flex gap-2 flex-wrap">
          {r.model_cards.map(mc => (
            <div key={mc.name} className="card card-sm" style={{flex:1, minWidth:200}}>
              <div className="fw-600" style={{fontSize:'.8rem'}}>{mc.role}</div>
              <div className="txt-mono" style={{fontSize:'.72rem', color:'var(--accent-teal)'}}>{mc.name}</div>
              <div className="txt-3" style={{fontSize:'.68rem', marginTop:'.2rem'}}>
                Family: <strong style={{color:'var(--txt)'}}>{mc.family}</strong> · Rev: {mc.revision}
              </div>
            </div>
          ))}
        </div>
        <div className="alert alert-info mt-2" style={{fontSize:'.75rem'}}>
          <span>ℹ</span>
          <span>INV-02: Proposer family (MiniLM) ≠ Verifier family (DeBERTa). Family guard checked at startup and each gate run.</span>
        </div>
      </div>

      <div className="section-title">False-Accept Rates (lower is better)</div>
      <div className="grid" style={{gridTemplateColumns:'repeat(4,1fr)', gap:'.75rem', marginBottom:'1.5rem'}}>
        {stages.map(s => (
          <RateCard key={s.key}
            label={`${s.label} — FA`}
            n={r.stages[s.key].false_accept_n}
            rate={r.stages[s.key].false_accept_rate}
            ci={r.stages[s.key].false_accept_ci}
            total={r.stages[s.key].total}
            note={s.key === 'overall' ? `Hard-neg FA: ${r.stages.overall.hard_neg_false_accept}/20` : null}
          />
        ))}
      </div>

      <div className="section-title">False-Reject Rates (lower is better)</div>
      <div className="grid" style={{gridTemplateColumns:'repeat(4,1fr)', gap:'.75rem', marginBottom:'1.5rem'}}>
        {stages.map(s => (
          <RateCard key={s.key}
            label={`${s.label} — FR`}
            n={r.stages[s.key].false_reject_n}
            rate={r.stages[s.key].false_reject_rate}
            ci={r.stages[s.key].false_reject_ci}
            total={r.stages[s.key].total}
          />
        ))}
      </div>

      <div className="card">
        <div className="section-title" style={{color:'var(--sev-high)'}}>
          Named Residual Risk Statement (INV-15)
        </div>
        <div className="alert alert-warning mb-2">
          <span>⚠</span>
          <strong>This risk is not hidden. It is measured and stated explicitly.</strong>
        </div>
        <p style={{fontSize:'.9rem', lineHeight:1.7}}>
          {r.residual_risk_line} — <strong>{r.residual_risk_rate}</strong>
        </p>
        <pre style={{
          fontFamily:'var(--mono)', fontSize:'.75rem', color:'var(--txt-2)',
          background:'var(--bg)', padding:'1rem', borderRadius:'var(--r-md)',
          border:'1px solid var(--border)', whiteSpace:'pre-wrap', lineHeight:1.7,
        }}>
          {r.residual_risk}
        </pre>
      </div>
    </div>
  )
}
