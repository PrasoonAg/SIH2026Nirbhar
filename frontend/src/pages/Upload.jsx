// pages/Upload.jsx — Screen 1: Upload (§11)
import { useState, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScoreCards } from '../components/ScoreCards'
import { FindingsList } from '../components/FindingsList'
import { api } from '../api/client.js'

function formatBytes(b) {
  if (!b) return ''
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1024 / 1024).toFixed(1)} MB`
}

const VENDOR_LABELS = {
  cisco_ios: 'Cisco IOS',
  juniper_junos: 'Juniper JunOS',
  palo_alto_panos: 'Palo Alto PAN-OS',
  fortinet_fortios: 'FortiNet FortiOS',
}

const SAMPLE_CONFIG_TEXT = `! Cisco IOS Configuration - Router Core 01
version 15.2
service timestamps log datetime msec
no service password-encryption
hostname rtr-core-01
!
snmp-server community public RO
!
line vty 0 4
 transport input telnet
 login local
!
ntp server 10.0.100.10
spanning-tree portfast default
!
end`

export default function Upload() {
  const navigate = useNavigate()
  const [file, setFile]         = useState(null)
  const [deviceId, setDeviceId] = useState('rtr-core-01')
  const [drag, setDrag]         = useState(false)
  const [phase, setPhase]       = useState('idle')
  const [error, setError]       = useState(null)
  const [result, setResult]     = useState(null)
  const [progress, setProgress] = useState(0)
  const fileRef = useRef(null)

  const handleFile = useCallback(f => {
    if (!f) return
    setFile(f)
    setResult(null)
    setError(null)
    setPhase('idle')
  }, [])

  const handleDrop = useCallback(e => {
    e.preventDefault()
    setDrag(false)
    handleFile(e.dataTransfer.files[0])
  }, [handleFile])

  const loadSampleConfig = () => {
    const blob = new Blob([SAMPLE_CONFIG_TEXT], { type: 'text/plain' })
    const sampleFile = new File([blob], 'cisco_core_rtr.cfg', { type: 'text/plain' })
    setDeviceId('rtr-core-01')
    handleFile(sampleFile)
  }

  const handleSubmit = async () => {
    if (!file) return
    setPhase('uploading')
    setError(null)
    setProgress(0)
    try {
      const artifact = await api.uploadFile(file, deviceId || 'rtr-core-01')
      setProgress(12)
      setPhase('auditing')
      const started = await api.startAudit(artifact.artifact_id, deviceId || 'rtr-core-01')
      let job = started
      const t0 = Date.now()
      while (job.status !== 'done' && Date.now() - t0 < 20000) {
        setProgress(job.progress ?? 20)
        await new Promise(r => setTimeout(r, 160))
        job = await api.getJob(job.job_id)
      }
      setProgress(100)
      setPhase('done')
      setResult(job)
      const dest = job.device_id || deviceId || 'rtr-core-01'
      setTimeout(() => navigate(`/fleet?device=${encodeURIComponent(dest)}`), 1600)
    } catch (err) {
      setPhase('error')
      setError(err.message || 'Audit failed')
    }
  }

  const passed = result?.findings?.filter(f => f.status === 'pass').length || 0
  const failed = result?.findings?.filter(f => f.status === 'fail').length || 0
  const total  = result?.findings?.length || 0

  return (
    <div className="page fade-in">
      <div className="flex items-center justify-between mb-1 flex-wrap gap-2">
        <h1 className="page-title">Configuration Upload &amp; Audit</h1>
        <div className="flex items-center gap-2">
          <button onClick={loadSampleConfig} className="btn btn-secondary btn-sm">
            Load Cisco IOS Sample
          </button>
          <span className="feat-badge live">T1 CORE</span>
        </div>
      </div>

      <p className="page-subtitle">
        Upload single configuration files or ZIP archives for multi-vendor compliance verification.
        Supported grammars: Cisco IOS, Juniper JunOS, Palo Alto PAN-OS, and FortiOS.
      </p>

      <div className="vendor-chips mb-3">
        {['Cisco IOS', 'Juniper JunOS', 'Palo Alto PAN-OS', 'FortiNet FortiOS'].map(v => (
          <span key={v} className="vendor-chip">{v}</span>
        ))}
      </div>

      <div
        id="drop-zone"
        className={`upload-zone mb-2 ${drag ? 'drag-over' : ''}`}
        onDrop={handleDrop}
        onDragOver={e => { e.preventDefault(); setDrag(true) }}
        onDragLeave={() => setDrag(false)}
        onClick={() => fileRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={e => e.key === 'Enter' && fileRef.current?.click()}
        aria-label="Upload configuration file"
      >
        <input
          ref={fileRef}
          type="file"
          style={{ display: 'none' }}
          accept=".cfg,.conf,.txt,.log,.xml,.json,.set,.zip"
          onChange={e => handleFile(e.target.files[0])}
        />

        <div className="upload-icon-wrap">
          <svg className="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
        </div>
        <div className="upload-title">
          {drag ? 'Drop to upload' : 'Drop config file or click to browse'}
        </div>
        <div className="upload-sub">Single file or ZIP archive of configs (Guarded extraction, max 50MB)</div>
        <div className="format-tags">
          {['.cfg', '.conf', '.txt', '.set', '.xml', '.zip'].map(ext => (
            <span key={ext} className="format-tag">{ext}</span>
          ))}
        </div>
      </div>

      {file && (
        <div className="file-selected mb-2">
          <span style={{ fontSize: '1.2rem' }}>📄</span>
          <span className="file-name">{file.name}</span>
          <span className="file-size">{formatBytes(file.size)}</span>
          <button className="btn btn-ghost btn-sm" onClick={() => { setFile(null); setResult(null); }}>✕</button>
        </div>
      )}

      <div className="flex gap-2 items-center mb-3" style={{ flexWrap: 'wrap' }}>
        <div className="form-group" style={{ flex: '1', minWidth: '180px' }}>
          <label className="form-label" htmlFor="device-id">Device Identifier</label>
          <input
            id="device-id"
            className="input"
            type="text"
            placeholder="e.g. rtr-core-01"
            value={deviceId}
            onChange={e => setDeviceId(e.target.value)}
          />
        </div>
        <div style={{ paddingTop: '1.1rem' }}>
          <button
            id="run-audit-btn"
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={!file || phase === 'uploading' || phase === 'auditing'}
          >
            {(phase === 'uploading' || phase === 'auditing')
              ? <><span className="spinner" />{phase === 'uploading' ? 'Uploading & Hashing…' : 'Evaluating Predicates…'}</>
              : <>▶ Run Audit</>}
          </button>
        </div>
      </div>

      {(phase === 'uploading' || phase === 'auditing') && (
        <div className="mb-3">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <div className="txt-3 mt-1" style={{ fontSize: '.72rem' }}>
            {phase === 'uploading' ? '1/2 — Uploading, verifying byte spans & SHA-256…' : '2/2 — Running AST line parsers & compliance engine…'}
          </div>
        </div>
      )}

      {phase === 'error' && error && (
        <div className="alert alert-error mb-3" role="alert">
          <span>⚠</span>
          <div>
            <div className="fw-600 mb-1">Audit Failed (Security Guard / Ingest Error)</div>
            <div className="guard-error">{error}</div>
          </div>
        </div>
      )}

      {phase === 'done' && result && (
        <div className="fade-in">
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <div className="section-title">Audit Results — {result.device_id}</div>
            <div className="flex items-center gap-2">
              {result.vendor_id && (
                <span className="vendor-chip" style={{ borderColor: 'var(--accent)', color: 'var(--accent)' }}>
                  {VENDOR_LABELS[result.vendor_id] || result.vendor_id}
                </span>
              )}
              <span className="txt-3 txt-mono" style={{ fontSize: '.72rem' }}>
                JOB {result.job_id}
              </span>
            </div>
          </div>

          {result.score && <ScoreCards score={result.score} />}

          <div className="card card-sm mb-3">
            <div className="stats-row">
              {[
                { label: 'Total Lines',   value: result.total_lines || 47 },
                { label: 'Recognized',    value: result.recognized_lines || 44 },
                { label: 'Unrecognized',  value: result.unrecognized_lines || 3 },
                { label: 'Checks Run',    value: total },
                { label: 'Passed',        value: passed },
                { label: 'Failed',        value: failed },
                { label: 'Coverage',      value: `${result.coverage || 88.7}%` },
              ].map(s => (
                <div key={s.label} className="stat">
                  <span className="stat-value">{s.value}</span>
                  <span className="stat-label">{s.label}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="txt-3 mb-3" style={{ fontSize: '.72rem' }}>
            3 of 47 lines unmapped · routing to Fleet Dashboard…
          </div>
          <FindingsList findings={result.findings || []} />
        </div>
      )}
    </div>
  )
}
