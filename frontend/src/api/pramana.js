// api/pramana.js — live fetch client against the backend DTOs.
// Do not import this from components; use api/client.js.
const BASE = '/api/v1'

async function parseError(res, fallback) {
  const err = await res.json().catch(() => ({ detail: res.statusText }))
  throw new Error(err.detail || fallback)
}

export async function uploadFile(file, deviceId = '') {
  const form = new FormData()
  form.append('file', file)
  if (deviceId) form.append('device_id', deviceId)

  const res = await fetch(`${BASE}/ingest/file`, { method: 'POST', body: form })
  if (!res.ok) await parseError(res, 'Upload failed')
  return res.json()
}

export async function startAudit(artifactId, deviceId, profileCommit = 'HEAD') {
  const res = await fetch(`${BASE}/audits`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ artifact_id: artifactId, device_id: deviceId, profile_commit: profileCommit }),
  })
  if (!res.ok) await parseError(res, 'Audit failed')
  return res.json()
}

export async function getJob(jobId) {
  const res = await fetch(`${BASE}/audits/${jobId}`)
  if (!res.ok) throw new Error(`Job ${jobId} not found`)
  return res.json()
}

export async function getFleet() {
  const res = await fetch(`${BASE}/fleet/summary`)
  if (!res.ok) await parseError(res, 'Fleet fetch failed')
  return res.json()
}

export async function getDevice(deviceId) {
  const res = await fetch(`${BASE}/fleet/devices/${encodeURIComponent(deviceId)}`)
  if (!res.ok) await parseError(res, 'Device fetch failed')
  return res.json()
}

export async function getTrainingQueue() {
  const res = await fetch(`${BASE}/training/queue`)
  if (!res.ok) await parseError(res, 'Training queue failed')
  return res.json()
}

export async function matchAnchors(signatureId) {
  const res = await fetch(`${BASE}/training/${encodeURIComponent(signatureId)}/anchors`)
  if (!res.ok) await parseError(res, 'Anchor match failed')
  return res.json()
}

export async function getTaxonomy() {
  const res = await fetch(`${BASE}/taxonomy`)
  if (!res.ok) await parseError(res, 'Taxonomy fetch failed')
  return res.json()
}

export async function submitMapping(body) {
  const res = await fetch(`${BASE}/mappings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) await parseError(res, 'Submit mapping failed')
  return res.json()
}

export async function getMappings() {
  const res = await fetch(`${BASE}/mappings`)
  if (!res.ok) await parseError(res, 'Mappings fetch failed')
  return res.json()
}

export async function getMapping(id) {
  const res = await fetch(`${BASE}/mappings/${encodeURIComponent(id)}`)
  if (!res.ok) await parseError(res, 'Mapping fetch failed')
  return res.json()
}

export async function secondReview(body) {
  const res = await fetch(`${BASE}/mappings/${encodeURIComponent(body.mappingId)}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) await parseError(res, 'Second review failed')
  return res.json()
}

export async function repropose(mappingId) {
  const res = await fetch(`${BASE}/mappings/${encodeURIComponent(mappingId)}/repropose`, { method: 'POST' })
  if (!res.ok) await parseError(res, 'Re-propose failed')
  return res.json()
}

export async function getSelfAudit() {
  const res = await fetch(`${BASE}/selfaudit/latest`)
  if (!res.ok) await parseError(res, 'Self-audit fetch failed')
  return res.json()
}

export async function getFixQueue() {
  const res = await fetch(`${BASE}/fix-impact`)
  if (!res.ok) await parseError(res, 'Fix-impact fetch failed')
  return res.json()
}

export async function simulateFix(body) {
  const res = await fetch(`${BASE}/sandbox/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) await parseError(res, 'Simulate failed')
  return res.json()
}

export async function getReports() {
  const res = await fetch(`${BASE}/reports`)
  if (!res.ok) await parseError(res, 'Reports fetch failed')
  return res.json()
}

export async function getReport(id) {
  const res = await fetch(`${BASE}/reports/${encodeURIComponent(id)}`)
  if (!res.ok) await parseError(res, 'Report fetch failed')
  return res.json()
}

export async function verifyReport(reportId, bytesSha) {
  const res = await fetch(`${BASE}/reports/${encodeURIComponent(reportId)}/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sha256: bytesSha }),
  })
  if (!res.ok) await parseError(res, 'Verify failed')
  return res.json()
}

export async function getLedger() {
  const res = await fetch(`${BASE}/ledger`)
  if (!res.ok) await parseError(res, 'Ledger fetch failed')
  return res.json()
}

export async function getAlerts() {
  const res = await fetch(`${BASE}/alerts`)
  if (!res.ok) await parseError(res, 'Alerts fetch failed')
  return res.json()
}

export async function ackAlert(id) {
  const res = await fetch(`${BASE}/alerts/${encodeURIComponent(id)}/ack`, { method: 'POST' })
  if (!res.ok) await parseError(res, 'Ack failed')
  return res.json()
}

export async function getFeatureRegistry() {
  const res = await fetch(`${BASE}/features`)
  if (!res.ok) await parseError(res, 'Feature registry fetch failed')
  return res.json()
}

export async function resetDemo() {
  return { ok: false, reason: 'live client — no mock store' }
}
