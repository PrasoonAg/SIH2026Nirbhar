// pages/Fleet.jsx — Screen 2: Fleet Dashboard / Triage (§11)
import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ScoreCards } from '../components/ScoreCards'
import { FindingsList } from '../components/FindingsList'
import { StateNode } from '../components/Badges'
import { useApi } from '../api/useApi.js'

const VENDOR_LABELS = {
  cisco_ios: 'Cisco IOS', juniper_junos: 'Juniper JunOS',
  palo_alto_panos: 'PAN-OS', fortinet_fortios: 'FortiOS',
}

function pct(num, den) {
  if (!den) return null
  return ((num / den) * 100).toFixed(1)
}

function DeviceCard({ dev, onClick, selected }) {
  const verified = pct(dev.score.verified_numerator, dev.score.verified_denominator)
  const failCount = (dev.findings || []).filter(f => f.status === 'fail').length
  const blastCount = (dev.findings || []).filter(f => f.blast_radius_flag).length
  const prov = (dev.mapping_summaries || []).filter(m => m.state === 'Provisional').length

  return (
    <div
      className="card mb-2"
      style={{
        cursor: 'pointer',
        borderColor: selected ? 'var(--accent)' : 'var(--border)',
        transition: 'all .2s'
      }}
      onClick={onClick}
    >
      <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
        <div>
          <div className="fw-600" style={{fontSize:'.9rem'}}>{dev.device_id}</div>
          <div className="txt-3" style={{fontSize:'.72rem'}}>{dev.site} · {VENDOR_LABELS[dev.vendor_id] || dev.vendor_id}</div>
        </div>
        <div className="flex items-center gap-2">
          {prov > 0 && <StateNode state="Provisional" />}
          {failCount > 0 && (
            <span style={{
              background:'rgba(248,113,113,.1)', color:'var(--sev-critical)',
              borderRadius:'99px', padding:'.1rem .55rem', fontSize:'.68rem', fontWeight:700
            }}>{failCount} failed</span>
          )}
          {blastCount > 0 && <span className="blast-badge">⚡ {blastCount}</span>}
        </div>
      </div>

      <div className="flex gap-3 flex-wrap">
        <div>
          <div className="score-label" style={{fontSize:'.62rem'}}>Verified</div>
          <div style={{
            fontSize:'1.3rem', fontWeight:800, fontFamily:'var(--mono)',
            color: verified >= 75 ? 'var(--accent-green)' : verified >= 50 ? 'var(--accent-amber)' : 'var(--sev-critical)'
          }}>{verified !== null ? `${verified}%` : 'n/a'}</div>
        </div>
        <div>
          <div className="score-label" style={{fontSize:'.62rem'}}>Provisional-Inclusive</div>
          <div style={{ fontSize:'1.3rem', fontWeight:800, fontFamily:'var(--mono)', color: 'var(--accent-amber)' }}>
            {pct(dev.score.provisional_inclusive_numerator, dev.score.provisional_inclusive_denominator) || 'n/a'}%
          </div>
        </div>
      </div>
    </div>
  )
}

export default function Fleet() {
  const { api, version } = useApi()
  const [params] = useSearchParams()
  const [devices, setDevices] = useState([])
  const [selected, setSelected] = useState(null)
  const [siteFilter, setSiteFilter] = useState('All')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancel = false
    setLoading(true)
    api.getFleet().then(data => {
      if (cancel) return
      const list = data.devices || []
      setDevices(list)
      const want = params.get('device') || data.lastUploadedDeviceId
      setSelected(list.find(d => d.device_id === want) || list[0] || null)
      setLoading(false)
    }).catch(() => setLoading(false))
    return () => { cancel = true }
  }, [params, version, api])

  const sites = ['All', ...new Set(devices.map(d => d.site))]
  const filtered = siteFilter === 'All' ? devices : devices.filter(d => d.site === siteFilter)

  return (
    <div className="page fade-in">
      <div className="flex items-center justify-between mb-1 flex-wrap gap-2">
        <div>
          <h1 className="page-title">Fleet Dashboard</h1>
          <p className="page-subtitle" style={{marginBottom:0}}>
            {devices.length} devices · {devices.flatMap(d=>d.findings || []).filter(f=>f.status==='fail').length} total findings
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="form-label">Site:</label>
          <select className="input select" style={{width:'auto'}}
            value={siteFilter} onChange={e => setSiteFilter(e.target.value)}>
            {sites.map(s => <option key={s}>{s}</option>)}
          </select>
        </div>
      </div>

      {loading && (
        <div className="card mb-3"><span className="spinner" /> Loading fleet…</div>
      )}

      <div className="grid-2 mb-3" style={{gridTemplateColumns:'340px 1fr'}}>
        <div>
          <div className="section-title">Devices</div>
          {filtered.map(dev => (
            <DeviceCard key={dev.device_id} dev={dev}
              selected={selected?.device_id === dev.device_id}
              onClick={() => setSelected(dev)} />
          ))}
        </div>

        {selected && (
          <div className="fade-in">
            <div className="section-title">
              {selected.device_id}
              <span className="vendor-chip" style={{marginLeft:'.5rem', borderColor:'var(--accent)', color:'var(--accent)'}}>
                {VENDOR_LABELS[selected.vendor_id]}
              </span>
            </div>

            <ScoreCards score={selected.score} />

            {(selected.mapping_summaries || []).length > 0 && (
              <div className="card card-sm mb-3">
                <div className="section-title">Mappings on this device</div>
                {selected.mapping_summaries.map(m => (
                  <div key={m.mapping_id} className="flex items-center gap-2 mb-1">
                    <StateNode state={m.state} />
                    <span className="txt-mono" style={{fontSize:'.75rem'}}>{m.setting_id}</span>
                  </div>
                ))}
              </div>
            )}

            <div className="section-title">
              Findings — {(selected.findings || []).filter(f=>f.status==='pass').length} passed · {(selected.findings || []).filter(f=>f.status==='fail').length} failed
            </div>
            <FindingsList findings={selected.findings} />

            <div className="divider" />
            <div className="flex gap-3 txt-3" style={{fontSize:'.72rem', fontFamily:'var(--mono)'}}>
              <span>Audited: {new Date(selected.audited_at).toLocaleString()}</span>
              <span>Profile: {selected.profile_commit}</span>
              {selected.unrecognized_lines != null && (
                <span>{selected.unrecognized_lines} of {selected.total_lines} lines unmapped</span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
