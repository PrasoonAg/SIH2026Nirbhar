// components/FindingsList.jsx
import { TrustBadge, SeverityBadge } from './Badges'

const CHECK_META = {
  'CHK-001': { title: 'Telnet management access enabled',         severity: 'CRITICAL' },
  'CHK-002': { title: 'Default SNMP community string in use',     severity: 'CRITICAL' },
  'CHK-003': { title: 'Management access not restricted by ACL',  severity: 'HIGH' },
  'CHK-004': { title: 'Remote syslog not configured',             severity: 'HIGH' },
  'CHK-005': { title: 'NTP not configured',                       severity: 'MEDIUM' },
  'CHK-006': { title: 'HTTP management server enabled (cleartext)',severity: 'HIGH' },
  'CHK-007': { title: 'TCP small servers enabled',                severity: 'MEDIUM' },
  'CHK-008': { title: 'UDP small servers enabled',                severity: 'MEDIUM' },
  'CHK-009': { title: 'Finger service enabled',                   severity: 'LOW' },
  'CHK-010': { title: 'SSH version 2 not enforced',               severity: 'HIGH' },
}

export function FindingsList({ findings = [] }) {
  if (!findings.length) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">📋</div>
        No findings to display
      </div>
    )
  }

  // Sort: fail first, then by severity weight
  const SEV_WEIGHT = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 }
  const sorted = [...findings].sort((a, b) => {
    if (a.status !== b.status) return a.status === 'pass' ? 1 : -1
    const ameta = CHECK_META[a.check_id]
    const bmeta = CHECK_META[b.check_id]
    const aw = SEV_WEIGHT[ameta?.severity] || 0
    const bw = SEV_WEIGHT[bmeta?.severity] || 0
    return bw - aw
  })

  return (
    <div className="findings-list">
      {sorted.map(f => {
        const meta = CHECK_META[f.check_id] || {}
        const sev = (meta.severity || 'LOW').toLowerCase()
        const isPassed = f.status === 'pass'

        return (
          <div
            key={f.check_id}
            className={`finding-row ${isPassed ? 'pass' : `fail ${sev}`} fade-in`}
          >
            <div className={`finding-status-icon ${f.status}`}>
              {isPassed ? '✓' : '✗'}
            </div>

            <div className="flex-col gap-1" style={{ flex: 1 }}>
              <div className="flex items-center gap-1 flex-wrap">
                <span className="finding-id">{f.check_id}</span>
                <span className="finding-title">{meta.title || f.check_id}</span>
              </div>
              <div className="finding-meta">
                <TrustBadge trust={f.trust || 'deterministic'} />
                {meta.severity && <SeverityBadge severity={meta.severity} />}
                {f.blast_radius_flag && (
                  <span className="blast-badge" title={f.blast_note || ''}>⚡ Blast Risk</span>
                )}
                {f.blast_note && (
                  <span className="txt-3" style={{fontSize:'.68rem'}}>{f.blast_note}</span>
                )}
                {f.unevaluated_reason && (
                  <span className="txt-3" style={{fontSize:'.68rem'}}>⚠ {f.unevaluated_reason}</span>
                )}
              </div>
            </div>

            {f.evidence_line_refs?.length > 0 && (
              <span className="txt-3" style={{fontSize:'.68rem', fontFamily:'var(--mono)'}}>
                {f.evidence_line_refs.length} ev.
              </span>
            )}
          </div>
        )
      })}
    </div>
  )
}
