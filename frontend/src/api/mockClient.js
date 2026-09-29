// Mock implementation of the same functions exported by pramana.js
import {
  getState, mutate, resetStore, appendLedger, clone, fullHash, GOLDEN_A_SCORE,
} from './mockStore'

function jitter(minMs, maxMs) {
  return minMs + Math.random() * (maxMs - minMs)
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms))
}

async function ordinary() {
  await sleep(jitter(150, 600))
}

async function embeddingLatency(sig) {
  if (sig?.ollama_fallback) {
    await sleep(jitter(9000, 13000))
    return
  }
  await sleep(jitter(200, 800))
}

function unknownGuardError(file) {
  if (!file) return null
  const name = (file.name || '').toLowerCase()
  if (name.endsWith('.exe') || name.endsWith('.bin')) {
    return 'ZIP guard / ingest: binary members rejected (NUL bytes / non-text). INV-16 redaction skipped; file not stored.'
  }
  return null
}

export async function uploadFile(file, deviceId = '') {
  await ordinary()
  const guard = unknownGuardError(file)
  if (guard) throw new Error(guard)

  const id = `art-${Date.now().toString(36)}`
  mutate(s => {
    s.jobs[`upload-${id}`] = {
      artifact_id: id,
      device_id: deviceId || 'rtr-core-01',
      filename: file?.name || 'config.cfg',
      created_at: new Date().toISOString(),
    }
  })
  return { artifact_id: id, sha256: fullHash(file?.name || 'config'), bytes: file?.size || 0 }
}

export async function startAudit(artifactId, deviceId, profileCommit = 'HEAD') {
  await ordinary()
  const jobId = `job-${Date.now().toString(36)}`
  const started = Date.now()
  const duration = 2000 + Math.random() * 200
  mutate(s => {
    s.jobs[jobId] = {
      job_id: jobId,
      artifact_id: artifactId,
      device_id: deviceId || 'rtr-core-01',
      profile_commit: profileCommit === 'HEAD' ? 'abc1234' : profileCommit,
      status: 'running',
      progress: 0,
      started,
      duration,
    }
  })
  return getJobSnapshot(jobId)
}

function getJobSnapshot(jobId) {
  const job = getState().jobs[jobId]
  if (!job) throw new Error(`Job ${jobId} not found`)
  const elapsed = Date.now() - job.started
  const progress = Math.min(100, Math.round((elapsed / job.duration) * 100))
  const done = progress >= 100
  if (done && job.status !== 'done') {
    finishJob(job)
  }
  const fresh = getState().jobs[jobId]
  return clone(fresh)
}

function finishJob(job) {
  const deviceId = job.device_id || 'rtr-core-01'
  mutate(s => {
    let dev = s.devices.find(d => d.device_id === deviceId)
    if (!dev) {
      dev = {
        device_id: deviceId,
        vendor_id: 'cisco_ios',
        site: 'Delhi HQ',
        audited_at: new Date().toISOString(),
        profile_commit: 'abc1234',
        coverage: 88.7,
        unrecognized_lines: 3,
        total_lines: 47,
        score: { ...GOLDEN_A_SCORE },
        findings: clone(s.devices[0].findings),
        mapping_summaries: [],
      }
      s.devices.unshift(dev)
    } else {
      dev.audited_at = new Date().toISOString()
      if (deviceId === 'rtr-core-01') {
        dev.score = { ...GOLDEN_A_SCORE }
      }
    }
    s.lastUploadedDeviceId = deviceId
    appendLedger('AuditCompleted', 'operator', deviceId)
    s.jobs[job.job_id] = {
      ...job,
      status: 'done',
      progress: 100,
      vendor_id: dev.vendor_id,
      total_lines: 47,
      recognized_lines: 44,
      unrecognized_lines: 3,
      coverage: dev.coverage,
      score: clone(dev.score),
      findings: clone(dev.findings),
      profile_commit: 'abc1234',
    }
  })
}

export async function getJob(jobId) {
  await sleep(jitter(80, 180))
  return getJobSnapshot(jobId)
}

export async function getFleet() {
  await ordinary()
  const s = getState()
  return {
    devices: clone(s.devices),
    lastUploadedDeviceId: s.lastUploadedDeviceId,
  }
}

export async function getDevice(deviceId) {
  await ordinary()
  const dev = getState().devices.find(d => d.device_id === deviceId)
  if (!dev) throw new Error(`Device ${deviceId} not found`)
  return clone(dev)
}

export async function getTrainingQueue() {
  await ordinary()
  return clone(getState().signatures)
}

export async function matchAnchors(signatureId) {
  const sig = getState().signatures.find(x => x.id === signatureId)
  if (!sig) throw new Error('Signature not found')
  await embeddingLatency(sig)
  return clone(sig)
}

export async function getTaxonomy() {
  await ordinary()
  return clone(getState().taxonomy)
}

function gateForSubmit(sig, target) {
  const wrong = sig.demo_fixture === 'wrong-control' || target === 'ip.source-route.disabled' && sig.redacted_line.includes('forward-protocol')
  if (wrong) {
    return {
      outcome: 'FAILED',
      nextState: 'Rejected',
      regen: {
        name: 'RegenCheck', verdict: 'PASS',
        detail: 'Byte-identical regen of the proposed spec — the line is well-formed, the control is wrong.',
        artifact: {
          type: 'hex-diff',
          snippet: '0000: 6e 6f 20 69 70 20 66 6f  72 77 61 72 64 2d 70 72\n0010: 6f 74 6f 63 6f 6c 20 6e  64                      | no ip forward-protocol nd\nΔ 00 bytes (regen PASS)',
        },
      },
      lexical: {
        name: 'LexicalCheck', verdict: 'FAIL',
        detail: 'Rank 4/10, BM25 3.11 < 6.00. Proposed target is a hard-negative sibling.',
        artifact: {
          type: 'bm25',
          rows: [
            { rank: 1, setting_id: 'ip.nd.forward-protocol', score: 11.02 },
            { rank: 2, setting_id: 'ip.directed-broadcast.disabled', score: 6.44 },
            { rank: 3, setting_id: 'ip.unreachable.disabled', score: 4.91 },
            { rank: 4, setting_id: 'ip.source-route.disabled', score: 3.11 },
            { rank: 5, setting_id: 'mgmt.telnet.enabled', score: 1.88 },
            { rank: 6, setting_id: 'snmp.community.default', score: 1.41 },
            { rank: 7, setting_id: 'ntp.server', score: 1.09 },
            { rank: 8, setting_id: 'logging.host', score: 0.92 },
            { rank: 9, setting_id: 'vty.access-class.in', score: 0.77 },
            { rank: 10, setting_id: 'stp.mode', score: 0.54 },
          ],
        },
      },
      second_model: {
        name: 'SecondModelCheck', verdict: 'FAIL',
        detail: 'DeBERTa rank 3, ranker score 0.31. Rank-1 is ip.nd.forward-protocol.',
        artifact: { type: 'ranker', rank: 3, score: 0.31 },
      },
    }
  }
  return {
    outcome: 'PASSED',
    nextState: 'Provisional',
    regen: {
      name: 'RegenCheck', verdict: 'PASS',
      detail: 'render(spec, match(spec, line)) == line  (12/12 support lines).',
      artifact: {
        type: 'hex-diff',
        snippet: '0000: 73 70 61 6e 6e 69 6e 67  2d 74 72 65 65 20 70 6f\n0010: 72 74 66 61 73 74 20 64  65 66 61 75 6c 74       | spanning-tree portfast default\nΔ 00 bytes (regen PASS)',
      },
    },
    lexical: {
      name: 'LexicalCheck', verdict: 'PASS',
      detail: 'Rank 1/10, BM25 12.47 ≥ 6.00.',
      artifact: {
        type: 'bm25',
        rows: [
          { rank: 1, setting_id: target, score: 12.47 },
          { rank: 2, setting_id: 'stp.mode', score: 7.12 },
          { rank: 3, setting_id: 'interface.switchport', score: 5.88 },
          { rank: 4, setting_id: 'vty.access-class.in', score: 2.04 },
          { rank: 5, setting_id: 'mgmt.ssh.v2', score: 1.66 },
          { rank: 6, setting_id: 'ntp.server', score: 1.21 },
          { rank: 7, setting_id: 'logging.host', score: 1.03 },
          { rank: 8, setting_id: 'snmp.community.default', score: 0.88 },
          { rank: 9, setting_id: 'routing.ospf.area', score: 0.71 },
          { rank: 10, setting_id: 'security.av.profile', score: 0.42 },
        ],
      },
    },
    second_model: {
      name: 'SecondModelCheck', verdict: 'PASS',
      detail: 'DeBERTa rank-1, ranker score 0.79 ≥ 0.55.',
      artifact: { type: 'ranker', rank: 1, score: 0.79 },
    },
  }
}

export async function submitMapping({ signatureId, target, actor = 'alice' }) {
  const sig = getState().signatures.find(x => x.id === signatureId)
  if (!sig) throw new Error('Signature not found')
  await embeddingLatency(sig)
  await ordinary()
  const gate = gateForSubmit(sig, target)
  const mappingId = `map-${Date.now().toString(36)}`
  const run = {
    gate_run_id: `gate-run-${Date.now().toString(36)}`,
    mapping_id: mappingId,
    run_at: new Date().toISOString(),
    outcome: gate.outcome,
    regen: gate.regen,
    lexical: gate.lexical,
    second_model: gate.second_model,
  }
  mutate(s => {
    const signature = s.signatures.find(x => x.id === signatureId)
    signature.state = gate.nextState
    const mapping = {
      id: mappingId,
      dialect_fingerprint: signature.dialect_fingerprint,
      vendor_id: signature.vendor_id,
      device_id: signature.device_id,
      redacted_line: signature.redacted_line,
      target_setting: target,
      first_admin_choice: target,
      first_admin: actor,
      state: gate.nextState,
      profile_commit: gate.nextState === 'Provisional' ? 'abc1234' : null,
      proposer_card: 'all-MiniLM-L6-v2',
      top1_cosine: signature.candidates[0]?.cosine,
      gate_runs: [run],
      evidence: gate.nextState === 'Provisional'
        ? [
            { id: `ev-${mappingId}-1`, cls: 'GATE_REGEN', actor: 'gate', weight: 0, reason: 'First-pass evidence; not corroborating.' },
            { id: `ev-${mappingId}-2`, cls: 'GATE_LEXICAL', actor: 'gate', weight: 0, reason: 'First-pass evidence; not corroborating.' },
            { id: `ev-${mappingId}-3`, cls: 'ADMIN_REVIEW', actor, weight: 0, reason: 'First-pass evidence; not corroborating.' },
          ]
        : [],
      ledger: [],
      supersedes: null,
      blind_pending: gate.nextState !== 'Rejected',
    }
    s.mappings.unshift(mapping)
    appendLedger(gate.nextState === 'Provisional' ? 'GatePassed' : 'Rejected', 'gate', signature.device_id)
    const dev = s.devices.find(d => d.device_id === signature.device_id)
    if (dev) {
      dev.mapping_summaries = [
        { mapping_id: mappingId, state: gate.nextState, setting_id: target },
        ...dev.mapping_summaries,
      ]
      if (gate.nextState === 'Provisional') {
        // Verified unchanged; Provisional-Inclusive ticks up so the two numbers diverge.
        dev.score = {
          ...dev.score,
          provisional_inclusive_numerator: Math.min(
            dev.score.provisional_inclusive_denominator,
            dev.score.provisional_inclusive_numerator + 3,
          ),
          provisional_dependence_numerator: Math.min(
            dev.score.provisional_inclusive_denominator,
            (dev.score.provisional_dependence_numerator || 0) + 3,
          ),
        }
      }
    }
  })
  return { mapping_id: mappingId, state: gate.nextState, gate: run }
}

export async function getMappings() {
  await ordinary()
  return clone(getState().mappings)
}

export async function getMapping(id) {
  await ordinary()
  const m = getState().mappings.find(x => x.id === id)
  if (!m) throw new Error('Mapping not found')
  return clone(m)
}

export async function secondReview({ mappingId, choice, actor = 'reviewer-2' }) {
  await ordinary()
  let result
  mutate(s => {
    const m = s.mappings.find(x => x.id === mappingId)
    if (!m) throw new Error('Mapping not found')
    if (m.state === 'Rejected') throw new Error('INV-01: Rejected is absorbing. Re-propose from scratch.')
    const agree = choice === m.first_admin_choice
    const sameActor = actor === m.first_admin
    const weight = sameActor ? 0 : agree ? 1 : 0
    m.blind_pending = false
    m.second_review = { actor, choice, weight, agree, sameActor }
    m.evidence.push({
      id: `ev-${mappingId}-rev`,
      cls: 'SECOND_REVIEWER',
      actor,
      weight,
      reason: sameActor ? 'Same actor as first admin — weight 0 (INV-06).' : agree ? 'Independent agreement.' : 'Disagreement recorded; blocks upgrade.',
    })
    if (agree && !sameActor && (m.state === 'Provisional' || m.state === 'AdminReviewed')) {
      m.state = 'Corroborated'
      const dev = s.devices.find(d => d.device_id === m.device_id)
      if (dev) {
        const row = dev.mapping_summaries.find(x => x.mapping_id === m.id)
        if (row) row.state = 'Corroborated'
        dev.score = {
          ...dev.score,
          verified_numerator: Math.min(dev.score.verified_denominator, dev.score.verified_numerator + 2),
        }
      }
      appendLedger('Corroborated', actor, m.device_id)
    } else {
      appendLedger('SecondReviewRecorded', actor, m.device_id)
    }
    result = clone(m)
  })
  return result
}

export async function repropose(mappingId) {
  await ordinary()
  const src = getState().mappings.find(x => x.id === mappingId)
  if (!src) throw new Error('Mapping not found')
  const newId = `map-${Date.now().toString(36)}`
  mutate(s => {
    const parent = s.mappings.find(x => x.id === mappingId)
    const neu = {
      ...clone(parent),
      id: newId,
      state: 'Unmapped',
      supersedes: mappingId,
      profile_commit: null,
      gate_runs: [],
      evidence: [],
      first_admin_choice: null,
      first_admin: null,
      blind_pending: true,
      target_setting: parent.target_setting,
    }
    s.mappings.unshift(neu)
    appendLedger('ReProposed', 'admin', parent.device_id)
    const sig = s.signatures.find(x => x.redacted_line === parent.redacted_line)
    if (sig) sig.state = 'Unmapped'
  })
  return { mapping_id: newId, supersedes: mappingId, state: 'Unmapped' }
}

export async function getSelfAudit() {
  await ordinary()
  return clone(getState().selfaudit)
}

export async function getFixQueue() {
  await ordinary()
  return clone(getState().fixQueue)
}

export async function simulateFix({ checkId, deviceId }) {
  await ordinary()
  const item = getState().fixQueue.find(q => q.check_id === checkId)
  if (!item) throw new Error('Fix item not found')
  const after = item.after_by_device[deviceId] || Object.values(item.after_by_device)[0]
  const log = {
    simulated_at: new Date().toISOString(),
    device_id: deviceId,
    check_id: checkId,
    profile_commit: 'abc1234',
    remediation_template: `compliance/templates/${checkId}.patch`,
    target_bytes_sha256: fullHash(`target:${deviceId}:${checkId}`),
    scratch_bytes_sha256: fullHash(`scratch:${deviceId}:${checkId}:${Date.now()}`),
    verdict: after.regressions?.length ? 'REGRESSION' : 'SUCCESS',
    before_score: item.before_score,
    after_score: { verified: after.verified, provisional: after.provisional, dependence: after.dependence },
    regressions: after.regressions || [],
    verified_delta: (after.verified - item.before_score.verified).toFixed(1),
    provisional_delta: (after.provisional - item.before_score.provisional).toFixed(1),
  }
  mutate(s => { s.simulations[`${checkId}:${deviceId}`] = log })
  return log
}

export async function getReports() {
  await ordinary()
  const s = getState()
  return s.devices.map(d => reportFromDevice(d, s))
}

function reportFromDevice(d, s) {
  const appendix_a = (d.mapping_summaries || [])
    .filter(m => m.state === 'Provisional')
    .map(m => {
      const full = s.mappings.find(x => x.id === m.mapping_id)
      return {
        mapping_id: m.mapping_id,
        setting_id: m.setting_id,
        top1_anchor: full?.redacted_line || m.setting_id,
        cosine: full?.top1_cosine ?? 0.87,
        gate_outcome: 'PASSED',
        evidence: full?.evidence || [],
      }
    })
  const id = `rpt-${d.device_id}`
  const header = {
    id,
    device_id: d.device_id,
    vendor_id: d.vendor_id,
    site: d.site,
    audited_at: d.audited_at,
    tool_version: '0.1.0-alpha',
    profile_commit: d.profile_commit,
    gate_config_hash: s.selfaudit.gate_config_hash,
    report_data_sha256: fullHash(JSON.stringify({ id, score: d.score, findings: d.findings.map(f => f.check_id) })),
    score: d.score,
    coverage: d.coverage,
    findings: d.findings,
    appendix_a,
    unevaluated: [],
    selfaudit_seed: s.selfaudit.seed,
    corpus_sha256: s.selfaudit.corpus_sha256,
    residual_risk_line: s.selfaudit.residual_risk_line,
    residual_risk_rate: s.selfaudit.residual_risk_rate,
  }
  return header
}

export async function getReport(id) {
  await ordinary()
  const reports = await getReportsFast()
  const r = reports.find(x => x.id === id)
  if (!r) throw new Error('Report not found')
  return r
}

function getReportsFast() {
  const s = getState()
  return s.devices.map(d => reportFromDevice(d, s))
}

export async function verifyReport(reportId, bytesSha) {
  await ordinary()
  const reports = getReportsFast()
  const r = reports.find(x => x.id === reportId)
  if (!r) throw new Error('Report not found')
  const ok = bytesSha === r.report_data_sha256
  return { ok, expected: r.report_data_sha256, observed: bytesSha }
}

export async function getLedger() {
  await ordinary()
  return clone(getState().ledger)
}

export async function getAlerts() {
  await ordinary()
  return clone(getState().alerts)
}

export async function ackAlert(id) {
  await ordinary()
  mutate(s => {
    const a = s.alerts.find(x => x.id === id)
    if (a) a.acknowledged = true
  })
  return { id, acknowledged: true }
}

export async function getFeatureRegistry() {
  await ordinary()
  return clone(getState().features.test_summary)
}

export async function resetDemo() {
  resetStore()
  return { ok: true }
}
