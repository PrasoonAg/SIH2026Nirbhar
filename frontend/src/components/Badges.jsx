// shared/TrustBadge.jsx
export function TrustBadge({ trust }) {
  const map = {
    deterministic: { cls: 'det', label: 'DETERMINISTIC' },
    corroborated:  { cls: 'corr', label: 'CORROBORATED' },
    provisional:   { cls: 'prov', label: 'PROVISIONAL' },
    rejected:      { cls: 'rej', label: 'REJECTED' },
    demoted:       { cls: 'rej', label: 'DEMOTED' },
  }
  const { cls, label } = map[(trust || '').toLowerCase()] || { cls: 'det', label: trust || 'DETERMINISTIC' }
  return <span className={`trust-badge ${cls}`}>{label}</span>
}

export function SeverityBadge({ severity }) {
  const s = (severity || '').toLowerCase()
  return <span className={`sev-badge ${s}`}>{(severity || '').toUpperCase()}</span>
}

export function StatusPill({ status }) {
  return <span className={`status-pill ${status}`}>{status}</span>
}

export function StateNode({ state }) {
  const map = {
    'Unmapped':     'unmapped',
    'Proposed':     'proposed',
    'AdminReviewed':'reviewed',
    'Gating':       'proposed',
    'Provisional':  'provisional',
    'ReVerification':'reviewed',
    'Corroborated': 'corroborated',
    'Rejected':     'rejected',
    'Demoted':      'rejected',
  }
  const cls = map[state] || 'unmapped'
  return <span className={`state-node ${cls}`}>{state}</span>
}
