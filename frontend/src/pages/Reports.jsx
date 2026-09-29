// pages/Reports.jsx — Screen 7
import { useEffect, useState } from 'react'
import { TrustBadge, SeverityBadge } from '../components/Badges'
import { ScoreCards } from '../components/ScoreCards'
import { FindingsList } from '../components/FindingsList'
import { useApi } from '../api/useApi.js'
import { downloadReportPdf } from '../pdf/reportPdf.js'

const VENDOR_LABELS = {
  cisco_ios: 'Cisco IOS', juniper_junos: 'Juniper JunOS',
  palo_alto_panos: 'PAN-OS', fortinet_fortios: 'FortiOS',
}

const CHECK_META = {
  'CHK-001': { title: 'Telnet management access enabled',          severity: 'CRITICAL' },
  'CHK-002': { title: 'Default SNMP community string in use',      severity: 'CRITICAL' },
  'CHK-003': { title: 'Management access not restricted by ACL',   severity: 'HIGH' },
  'CHK-004': { title: 'Remote syslog not configured',              severity: 'HIGH' },
  'CHK-005': { title: 'NTP not configured',                        severity: 'MEDIUM' },
  'CHK-006': { title: 'HTTP management server enabled',            severity: 'HIGH' },
  'CHK-010': { title: 'SSH version 2 not enforced',                severity: 'HIGH' },
}

export default function Reports() {
  const { api, version } = useApi()
  const [reports, setReports] = useState([])
  const [selected, setSelected] = useState(null)
  const [tab, setTab] = useState('findings')
  const [verify, setVerify] = useState(null)
  const [tamperedSha, setTamperedSha] = useState(null)

  useEffect(() => {
    api.getReports().then(rows => {
      setReports(rows)
      setSelected(cur => rows.find(r => r.id === cur?.id) || rows[0])
      setVerify(null)
      setTamperedSha(null)
    })
  }, [api, version])

  if (!selected) return <div className="page"><span className="spinner" /> Loading reports…</div>

  const runVerify = async (sha) => {
    const res = await api.verifyReport(selected.id, sha)
    setVerify(res)
  }

  const flipByte = () => {
    const orig = selected.report_data_sha256
    const flipped = orig.slice(0, -1) + (orig.endsWith('0') ? '1' : '0')
    setTamperedSha(flipped)
    runVerify(flipped)
  }

  return (
    <div className="page fade-in">
      <h1 className="page-title">Reports</h1>
      <p className="page-subtitle">
        Per-device compliance reports. Preview mirrors the downloaded PDF: header, both scores, findings, Appendix A, Appendix B.
      </p>

      <div className="flex gap-2 mb-3 flex-wrap">
        {reports.map(r => (
          <button key={r.id}
            className={`btn ${selected?.id === r.id ? 'btn-primary' : 'btn-secondary'} btn-sm`}
            onClick={() => { setSelected(r); setVerify(null); setTamperedSha(null) }}>
            {r.device_id}
          </button>
        ))}
      </div>

      <div className="fade-in" id="report-preview">
        <div className="card mb-3" style={{borderTop:'2px solid var(--accent)'}}>
          <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
            <div>
              <div className="fw-600" style={{fontSize:'1.1rem'}}>{selected.device_id}</div>
              <div className="txt-3" style={{fontSize:'.75rem'}}>
                {selected.site} · {VENDOR_LABELS[selected.vendor_id] || selected.vendor_id} · {new Date(selected.audited_at).toLocaleString()}
              </div>
            </div>
            <div className="flex gap-2">
              <button className="btn btn-primary btn-sm" id="download-pdf-btn" onClick={() => downloadReportPdf(selected)}>
                Download PDF
              </button>
              <button className="btn btn-secondary btn-sm" onClick={() => runVerify(tamperedSha || selected.report_data_sha256)}>
                Re-verify
              </button>
              <button className="btn btn-ghost btn-sm" onClick={flipByte}>
                Flip one byte (demo)
              </button>
            </div>
          </div>

          <div className="grid-3 mb-2" style={{gap:'.75rem'}}>
            {[
              ['Tool Version',   selected.tool_version],
              ['Profile Commit', selected.profile_commit],
              ['Gate Config Hash', selected.gate_config_hash],
              ['Coverage',       `${selected.coverage}%`],
              ['ReportData SHA-256', selected.report_data_sha256],
            ].map(([k, v]) => (
              <div key={k}>
                <div className="txt-3" style={{fontSize:'.65rem'}}>{k}</div>
                <div className="txt-mono" style={{fontSize:'.7rem', wordBreak:'break-all'}}>{v}</div>
              </div>
            ))}
          </div>
          {verify && (
            <div className={`alert ${verify.ok ? 'alert-success' : 'alert-error'} mt-2`}>
              <span>{verify.ok ? '✓' : '✗'}</span>
              <div>{verify.ok ? 'Re-verify PASS — bytes match ReportData SHA-256.' : 'Re-verify FAIL — flipped/tampered bytes do not match the chained hash.'}</div>
            </div>
          )}
        </div>

        <ScoreCards score={selected.score} />

        <div className="flex gap-2 mb-3" style={{borderBottom:'1px solid var(--border)', paddingBottom:'.5rem'}}>
          {[
            { id: 'findings', label: 'Findings' },
            { id: 'appendix_a', label: 'Appendix A — Evidence' },
            { id: 'appendix_b', label: 'Appendix B — Residual Risk' },
          ].map(t => (
            <button key={t.id}
              className={`btn btn-sm ${tab === t.id ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </div>

        {tab === 'findings' && (
          <div>
            {(selected.findings || []).filter(f => f.status === 'fail').map(f => {
              const meta = CHECK_META[f.check_id] || {}
              return (
                <div key={f.check_id} className="card mb-2">
                  <div className="flex items-center gap-2 mb-2 flex-wrap">
                    <span className="finding-id">{f.check_id}</span>
                    <span className="fw-600" style={{fontSize:'.88rem'}}>{meta.title}</span>
                    <div className="ml-auto flex gap-2">
                      <TrustBadge trust={f.trust || 'deterministic'} />
                      <SeverityBadge severity={meta.severity || 'LOW'} />
                      {f.blast_radius_flag && <span className="blast-badge">⚡ Blast Risk</span>}
                    </div>
                  </div>
                  {f.blast_note && <div className="txt-3 mb-2" style={{fontSize:'.75rem'}}>{f.blast_note}</div>}
                  {f.line_ref && (
                    <div className="mb-2">
                      <div className="txt-3" style={{fontSize:'.68rem'}}>Line {f.line_ref.line_no}:</div>
                      <div className="code-line">{f.line_ref.redacted_text}</div>
                    </div>
                  )}
                  {f.remediation?.diff && (
                    <pre className="code-line" style={{whiteSpace:'pre-wrap'}}>{f.remediation.diff}</pre>
                  )}
                </div>
              )
            })}
            <div className="section-title">All Findings</div>
            <FindingsList findings={selected.findings} />
          </div>
        )}

        {tab === 'appendix_a' && (
          <div>
            <div className="section-title">Appendix A — Evidence for Provisional Mappings</div>
            <div className="card">
              {!(selected.appendix_a || []).length ? (
                <div className="txt-3">No Provisional mappings used in this report.</div>
              ) : selected.appendix_a.map(item => (
                <div key={item.mapping_id} className="mb-3">
                  <div className="fw-600 mb-1">{item.mapping_id}</div>
                  <div className="grid-2 mb-2" style={{gap:'.75rem'}}>
                    {[
                      ['Setting ID', item.setting_id],
                      ['Top-1 Anchor', item.top1_anchor],
                      ['Cosine', String(item.cosine)],
                      ['Gate', item.gate_outcome],
                    ].map(([k, v]) => (
                      <div key={k}>
                        <div className="txt-3" style={{fontSize:'.65rem'}}>{k}</div>
                        <div className="txt-mono" style={{fontSize:'.78rem'}}>{v}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === 'appendix_b' && (
          <div>
            <div className="section-title">Appendix B — Residual Risk &amp; Self-Audit (INV-15)</div>
            <div className="alert alert-warning mb-3">
              <span>⚠</span>
              <div>
                <div className="fw-600 mb-1">This risk is stated, not hidden.</div>
                <div style={{fontSize:'.8rem'}}>
                  {selected.residual_risk_line} Measured rate: <strong>{selected.residual_risk_rate}</strong>
                </div>
              </div>
            </div>
            <div className="card">
              <div className="grid-3" style={{gap:'.75rem'}}>
                {[['Seed', String(selected.selfaudit_seed)], ['Corpus SHA', selected.corpus_sha256], ['Gate Config Hash', selected.gate_config_hash]].map(([k,v]) => (
                  <div key={k}>
                    <div className="txt-3" style={{fontSize:'.65rem'}}>{k}</div>
                    <div className="txt-mono" style={{fontSize:'.7rem', wordBreak:'break-all'}}>{v}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
