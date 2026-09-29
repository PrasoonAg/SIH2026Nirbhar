// In-memory demo store. Session-scoped. Reset via ?reset=1 or Ctrl+Alt+R.
// Components never import this directly for reads — they go through the API client.

const listeners = new Set()
let version = 0

export function subscribe(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function getVersion() {
  return version
}

function notify() {
  version += 1
  listeners.forEach(fn => fn())
}

function sha256like(input) {
  let h1 = 0x811c9dc5
  let h2 = 0x01000193
  const s = String(input)
  for (let i = 0; i < s.length; i++) {
    h1 ^= s.charCodeAt(i)
    h1 = Math.imul(h1, 0x01000193)
    h2 = Math.imul(h2 ^ (s.charCodeAt(i) * (i + 17)), 0x85ebca6b)
    h2 ^= h2 >>> 13
  }
  const hex = n => (n >>> 0).toString(16).padStart(8, '0')
  let out = ''
  for (let i = 0; i < 8; i++) {
    out += hex(h1 ^ Math.imul(h2, i + 3))
    out += hex((h2 + i * 0x9e3779b9) ^ h1)
  }
  return out.slice(0, 64)
}

export function fullHash(input) {
  return `sha256:${sha256like(input)}`
}

const GOLDEN_A_SCORE = {
  verified_numerator: 25,
  verified_denominator: 35,
  provisional_inclusive_numerator: 35,
  provisional_inclusive_denominator: 47,
  provisional_dependence_numerator: 12,
}

const TELNET_BLAST =
  'disabling Telnet while SSH is absent — removes remote management access'

const CHECK_META = {
  'CHK-001': { title: 'Telnet management access enabled', severity: 'CRITICAL' },
  'CHK-002': { title: 'Default SNMP community string in use', severity: 'CRITICAL' },
  'CHK-003': { title: 'Management access not restricted by ACL', severity: 'HIGH' },
  'CHK-004': { title: 'Remote syslog not configured', severity: 'HIGH' },
  'CHK-005': { title: 'NTP not configured', severity: 'MEDIUM' },
  'CHK-006': { title: 'HTTP management server enabled (cleartext)', severity: 'HIGH' },
  'CHK-007': { title: 'TCP small servers enabled', severity: 'MEDIUM' },
  'CHK-008': { title: 'UDP small servers enabled', severity: 'MEDIUM' },
  'CHK-009': { title: 'Finger service enabled', severity: 'LOW' },
  'CHK-010': { title: 'SSH version 2 not enforced', severity: 'HIGH' },
}

export { CHECK_META, GOLDEN_A_SCORE, TELNET_BLAST }

function findingsCore() {
  return [
    {
      check_id: 'CHK-001', status: 'fail', trust: 'deterministic', blast_radius_flag: true,
      blast_note: TELNET_BLAST, evidence_line_refs: [42],
      line_ref: { line_no: 42, redacted_text: 'transport input telnet' },
      framework_refs: [{ ctrl: 'AC-17', source: 'NIST 800-53 Rev.5', verified: false }],
      remediation: { diff: '- transport input telnet\n+ transport input ssh' },
    },
    {
      check_id: 'CHK-002', status: 'fail', trust: 'deterministic', blast_radius_flag: false,
      evidence_line_refs: [108],
      line_ref: { line_no: 108, redacted_text: 'snmp-server community public RO' },
      framework_refs: [{ ctrl: 'CM-7', source: 'NIST 800-53 Rev.5', verified: false }],
      remediation: { diff: '- snmp-server community public RO\n+ snmp-server community <REDACTED> RO' },
    },
    { check_id: 'CHK-003', status: 'pass', trust: 'deterministic', blast_radius_flag: false, evidence_line_refs: [15] },
    { check_id: 'CHK-004', status: 'fail', trust: 'deterministic', blast_radius_flag: false, evidence_line_refs: [] },
    { check_id: 'CHK-005', status: 'pass', trust: 'provisional', blast_radius_flag: false, evidence_line_refs: [55] },
    { check_id: 'CHK-010', status: 'pass', trust: 'deterministic', blast_radius_flag: false, evidence_line_refs: [60] },
  ]
}

function clone(v) {
  return JSON.parse(JSON.stringify(v))
}

function seedLedger() {
  const events = [
    { event: 'LineUnrecognized', actor: 'system', device: 'rtr-core-01', ts: '2026-09-29T10:00:01Z' },
    { event: 'AnchorMatched', actor: 'proposer', device: 'rtr-core-01', ts: '2026-09-29T10:00:02Z' },
    { event: 'AdminConfirmed', actor: 'alice', device: 'rtr-core-01', ts: '2026-09-29T10:01:00Z' },
    { event: 'GateFired', actor: 'gate', device: 'rtr-core-01', ts: '2026-09-29T10:01:01Z' },
    { event: 'GatePassed', actor: 'gate', device: 'rtr-core-01', ts: '2026-09-29T10:01:03Z' },
    { event: 'ProfileCommit', actor: 'system', device: 'rtr-core-01', ts: '2026-09-29T10:01:04Z' },
    { event: 'LineUnrecognized', actor: 'system', device: 'fw-perimeter-01', ts: '2026-09-29T10:05:00Z' },
    { event: 'AdminConfirmed', actor: 'bob', device: 'fw-perimeter-01', ts: '2026-09-29T10:05:30Z' },
    { event: 'GateFired', actor: 'gate', device: 'fw-perimeter-01', ts: '2026-09-29T10:05:31Z' },
    { event: 'GateFailed', actor: 'gate', device: 'fw-perimeter-01', ts: '2026-09-29T10:05:33Z' },
    { event: 'Rejected', actor: 'gate', device: 'fw-perimeter-01', ts: '2026-09-29T10:05:33Z' },
    { event: 'Demoted', actor: 'decay', device: 'fw-edge-01', ts: '2026-09-29T11:22:08Z' },
  ]
  const rows = []
  let prev = null
  events.forEach((e, i) => {
    const payload = `${i + 1}|${e.event}|${e.actor}|${e.device}|${e.ts}|${prev || 'GENESIS'}`
    const hash = fullHash(payload)
    rows.push({
      seq: i + 1,
      ...e,
      hash,
      prev_hash: prev,
      chain_ok: true,
    })
    prev = hash
  })
  return rows
}

function seedState() {
  const devices = [
    {
      device_id: 'rtr-core-01',
      vendor_id: 'cisco_ios',
      site: 'Delhi HQ',
      audited_at: '2026-09-29T10:30:00Z',
      profile_commit: 'abc1234',
      coverage: 88.7,
      unrecognized_lines: 3,
      total_lines: 47,
      score: { ...GOLDEN_A_SCORE },
      findings: findingsCore(),
      mapping_summaries: [
        { mapping_id: 'map-001', state: 'Provisional', setting_id: 'stp.portfast.default' },
      ],
    },
    {
      device_id: 'rtr-core-02',
      vendor_id: 'juniper_junos',
      site: 'Hyderabad DC',
      audited_at: '2026-09-29T11:12:00Z',
      profile_commit: 'abc1234',
      coverage: 93.4,
      unrecognized_lines: 2,
      total_lines: 61,
      score: {
        verified_numerator: 28, verified_denominator: 35,
        provisional_inclusive_numerator: 33, provisional_inclusive_denominator: 47,
        provisional_dependence_numerator: 5,
      },
      findings: [
        { check_id: 'CHK-004', status: 'fail', trust: 'deterministic', blast_radius_flag: false, evidence_line_refs: [22] },
        { check_id: 'CHK-001', status: 'pass', trust: 'deterministic', blast_radius_flag: false, evidence_line_refs: [] },
        { check_id: 'CHK-010', status: 'pass', trust: 'deterministic', blast_radius_flag: false, evidence_line_refs: [] },
      ],
      mapping_summaries: [],
    },
    {
      device_id: 'fw-perimeter-01',
      vendor_id: 'palo_alto_panos',
      site: 'Mumbai DR',
      audited_at: '2026-09-29T11:00:00Z',
      profile_commit: 'abc1234',
      coverage: 91.2,
      unrecognized_lines: 1,
      total_lines: 88,
      score: {
        verified_numerator: 30, verified_denominator: 35,
        provisional_inclusive_numerator: 42, provisional_inclusive_denominator: 47,
        provisional_dependence_numerator: 5,
      },
      findings: [
        { check_id: 'CHK-001', status: 'pass', trust: 'deterministic', blast_radius_flag: false },
        { check_id: 'CHK-002', status: 'pass', trust: 'deterministic', blast_radius_flag: false },
        { check_id: 'CHK-003', status: 'pass', trust: 'deterministic', blast_radius_flag: false },
        { check_id: 'CHK-004', status: 'fail', trust: 'deterministic', blast_radius_flag: false },
        { check_id: 'CHK-005', status: 'pass', trust: 'provisional', blast_radius_flag: false },
        { check_id: 'CHK-010', status: 'fail', trust: 'deterministic', blast_radius_flag: false },
      ],
      mapping_summaries: [],
    },
    {
      device_id: 'fw-edge-01',
      vendor_id: 'fortinet_fortios',
      site: 'Bengaluru PoP',
      audited_at: '2026-09-29T09:44:00Z',
      profile_commit: 'abc1234',
      coverage: 86.3,
      unrecognized_lines: 4,
      total_lines: 73,
      score: {
        verified_numerator: 22, verified_denominator: 35,
        provisional_inclusive_numerator: 31, provisional_inclusive_denominator: 47,
        provisional_dependence_numerator: 9,
      },
      findings: [
        { check_id: 'CHK-006', status: 'fail', trust: 'deterministic', blast_radius_flag: false },
        { check_id: 'CHK-002', status: 'fail', trust: 'deterministic', blast_radius_flag: false },
        { check_id: 'CHK-010', status: 'pass', trust: 'corroborated', blast_radius_flag: false },
      ],
      mapping_summaries: [
        { mapping_id: 'map-003', state: 'Demoted', setting_id: 'security.ips.sensor' },
      ],
    },
    {
      device_id: 'sw-access-02',
      vendor_id: 'cisco_ios',
      site: 'Delhi HQ',
      audited_at: '2026-09-29T09:00:00Z',
      profile_commit: 'abc1234',
      coverage: 72.8,
      unrecognized_lines: 7,
      total_lines: 39,
      score: {
        verified_numerator: 10, verified_denominator: 35,
        provisional_inclusive_numerator: 18, provisional_inclusive_denominator: 47,
        provisional_dependence_numerator: 8,
      },
      findings: [
        {
          check_id: 'CHK-001', status: 'fail', trust: 'deterministic', blast_radius_flag: true,
          blast_note: TELNET_BLAST, evidence_line_refs: [18],
        },
        { check_id: 'CHK-002', status: 'fail', trust: 'deterministic', blast_radius_flag: false },
        { check_id: 'CHK-006', status: 'fail', trust: 'deterministic', blast_radius_flag: false },
        { check_id: 'CHK-010', status: 'fail', trust: 'deterministic', blast_radius_flag: false },
      ],
      mapping_summaries: [],
    },
    {
      device_id: 'rtr-edge-03',
      vendor_id: 'cisco_ios',
      site: 'Chennai Edge',
      audited_at: '2026-09-29T08:18:00Z',
      profile_commit: 'abc1234',
      coverage: 81.6,
      unrecognized_lines: 5,
      total_lines: 54,
      score: {
        verified_numerator: 21, verified_denominator: 35,
        provisional_inclusive_numerator: 21, provisional_inclusive_denominator: 47,
        provisional_dependence_numerator: 0,
      },
      findings: [
        {
          check_id: 'CHK-001', status: 'fail', trust: 'deterministic', blast_radius_flag: true,
          blast_note: TELNET_BLAST,
        },
        { check_id: 'CHK-009', status: 'fail', trust: 'provisional', blast_radius_flag: false },
      ],
      mapping_summaries: [],
    },
  ]

  const signatures = [
    {
      id: 'sig-001',
      dialect_fingerprint: 'a3f2b1c9',
      vendor_id: 'cisco_ios',
      device_id: 'rtr-edge-03',
      redacted_line: 'spanning-tree portfast default',
      occurrences: 14,
      ollama_fallback: false,
      demo_fixture: 'unseen-confirm',
      candidates: [
        { setting_id: 'stp.portfast.default', phrase: 'Enable PortFast globally on access ports', cosine: 0.87 },
        { setting_id: 'stp.mode', phrase: 'Set spanning-tree mode (RSTP/PVST)', cosine: 0.74 },
        { setting_id: 'interface.switchport', phrase: 'Switchport access or trunk mode', cosine: 0.61 },
      ],
      state: 'Unmapped',
    },
    {
      id: 'sig-002',
      dialect_fingerprint: 'b9d3e7f1',
      vendor_id: 'juniper_junos',
      device_id: 'rtr-core-02',
      redacted_line: 'set protocols ospf area 0.0.0.0 interface lo0.0 passive',
      occurrences: 3,
      ollama_fallback: false,
      candidates: [
        { setting_id: 'routing.ospf.passive-interface', phrase: 'OSPF passive interface (no hello)', cosine: 0.88 },
        { setting_id: 'routing.ospf.area', phrase: 'OSPF area configuration', cosine: 0.75 },
        { setting_id: 'routing.ospf.metric', phrase: 'OSPF metric / cost', cosine: 0.51 },
      ],
      state: 'Proposed',
    },
    {
      id: 'sig-wrong-control',
      dialect_fingerprint: 'zz99ff12',
      vendor_id: 'cisco_ios',
      device_id: 'rtr-core-01',
      redacted_line: 'no ip forward-protocol nd',
      occurrences: 2,
      ollama_fallback: false,
      demo_fixture: 'wrong-control',
      candidates: [
        { setting_id: 'ip.source-route.disabled', phrase: 'Disable IP source-route (wrong sibling control)', cosine: 0.83 },
        { setting_id: 'ip.directed-broadcast.disabled', phrase: 'Disable IP directed-broadcast', cosine: 0.71 },
        { setting_id: 'ip.unreachable.disabled', phrase: 'Disable ICMP unreachables', cosine: 0.58 },
      ],
      state: 'Unmapped',
    },
    {
      id: 'sig-003',
      dialect_fingerprint: 'c1a4e8d2',
      vendor_id: 'fortinet_fortios',
      device_id: 'fw-edge-01',
      redacted_line: 'set ips-sensor "default"',
      occurrences: 1,
      ollama_fallback: false,
      candidates: [
        { setting_id: 'security.ips.sensor', phrase: 'IPS/IDS sensor profile applied to policy', cosine: 0.84 },
        { setting_id: 'security.av.profile', phrase: 'Antivirus profile on firewall policy', cosine: 0.62 },
        { setting_id: 'security.waf.profile', phrase: 'WAF profile applied to traffic', cosine: 0.44 },
      ],
      state: 'Unmapped',
    },
    {
      id: 'sig-ollama',
      dialect_fingerprint: 'e7c0aa11',
      vendor_id: 'palo_alto_panos',
      device_id: 'fw-perimeter-01',
      redacted_line: 'set deviceconfig system panorama-server 10.4.8.21',
      occurrences: 1,
      ollama_fallback: true,
      candidates: [
        { setting_id: 'mgmt.logging.host', phrase: 'Remote logging destination', cosine: 0.41 },
        { setting_id: 'ntp.server', phrase: 'NTP server association', cosine: 0.33 },
        { setting_id: 'snmp.community.default', phrase: 'Default SNMP community', cosine: 0.29 },
      ],
      state: 'Unmapped',
    },
  ]

  const mappings = [
    {
      id: 'map-001',
      dialect_fingerprint: 'a3f2b1c9',
      vendor_id: 'cisco_ios',
      device_id: 'rtr-core-01',
      redacted_line: 'spanning-tree portfast default',
      target_setting: 'stp.portfast.default',
      first_admin_choice: 'stp.portfast.default',
      first_admin: 'alice',
      state: 'Provisional',
      profile_commit: 'abc1234',
      proposer_card: 'all-MiniLM-L6-v2',
      top1_cosine: 0.87,
      gate_runs: [
        {
          gate_run_id: 'gate-run-001',
          mapping_id: 'map-001',
          run_at: '2026-09-29T09:00:00Z',
          outcome: 'PASSED',
          regen: {
            name: 'RegenCheck', verdict: 'PASS',
            detail: 'All 12 support lines round-tripped.',
            artifact: {
              type: 'hex-diff',
              snippet: '0000: 73 70 61 6e 6e 69 6e 67  2d 74 72 65 65 20 70 6f\n0010: 72 74 66 61 73 74 20 64  65 66 61 75 6c 74       | spanning-tree portfast default',
            },
          },
          lexical: {
            name: 'LexicalCheck', verdict: 'PASS',
            detail: 'Rank 1/10, BM25 12.47 ≥ 6.00.',
            artifact: {
              type: 'bm25',
              rows: [
                { rank: 1, setting_id: 'stp.portfast.default', score: 12.47 },
                { rank: 2, setting_id: 'stp.mode', score: 7.12 },
                { rank: 3, setting_id: 'interface.switchport', score: 5.88 },
              ],
            },
          },
          second_model: {
            name: 'SecondModelCheck', verdict: 'PASS',
            detail: 'DeBERTa rank-1, score 0.79 ≥ 0.55.',
            artifact: { type: 'ranker', rank: 1, score: 0.79 },
          },
        },
      ],
      evidence: [
        { id: 'ev-001', cls: 'GATE_REGEN', actor: 'gate', weight: 0, reason: 'First-pass evidence; not corroborating.' },
        { id: 'ev-002', cls: 'GATE_SECOND_MODEL', actor: 'gate', weight: 0, reason: 'First-pass evidence; not corroborating.' },
        { id: 'ev-003', cls: 'ADMIN_REVIEW', actor: 'alice', weight: 0, reason: 'First-pass evidence; not corroborating.' },
      ],
      ledger: [],
      supersedes: null,
      blind_pending: true,
    },
    {
      id: 'map-002',
      dialect_fingerprint: 'zz99ff12',
      vendor_id: 'cisco_ios',
      device_id: 'rtr-core-01',
      redacted_line: 'no ip forward-protocol nd',
      target_setting: 'ip.source-route.disabled',
      first_admin_choice: 'ip.source-route.disabled',
      first_admin: 'bob',
      state: 'Rejected',
      profile_commit: null,
      proposer_card: 'all-MiniLM-L6-v2',
      top1_cosine: 0.83,
      gate_runs: [
        {
          gate_run_id: 'gate-run-002',
          mapping_id: 'map-002',
          run_at: '2026-09-29T08:00:00Z',
          outcome: 'FAILED',
          regen: {
            name: 'RegenCheck', verdict: 'PASS',
            detail: '5/5 lines round-tripped (wrong control still renders).',
            artifact: {
              type: 'hex-diff',
              snippet: '0000: 6e 6f 20 69 70 20 66 6f  72 77 61 72 64 2d 70 72\n0010: 6f 74 6f 63 6f 6c 20 6e  64                      | no ip forward-protocol nd',
            },
          },
          lexical: {
            name: 'LexicalCheck', verdict: 'FAIL',
            detail: 'Rank 4/10, BM25 3.11 < 6.00. Wrong control.',
            artifact: {
              type: 'bm25',
              rows: [
                { rank: 1, setting_id: 'ip.nd.forward-protocol', score: 11.02 },
                { rank: 2, setting_id: 'ip.directed-broadcast.disabled', score: 6.44 },
                { rank: 3, setting_id: 'ip.unreachable.disabled', score: 4.91 },
                { rank: 4, setting_id: 'ip.source-route.disabled', score: 3.11 },
              ],
            },
          },
          second_model: {
            name: 'SecondModelCheck', verdict: 'FAIL',
            detail: 'DeBERTa rank 3. Correct target at rank 1. Ranker score 0.31.',
            artifact: { type: 'ranker', rank: 3, score: 0.31 },
          },
        },
      ],
      evidence: [],
      ledger: [],
      supersedes: null,
      blind_pending: false,
    },
    {
      id: 'map-003',
      dialect_fingerprint: 'c1a4e8d2',
      vendor_id: 'fortinet_fortios',
      device_id: 'fw-edge-01',
      redacted_line: 'set ips-sensor "default"',
      target_setting: 'security.ips.sensor',
      first_admin_choice: 'security.ips.sensor',
      first_admin: 'carol',
      state: 'Demoted',
      profile_commit: 'abc1234',
      proposer_card: 'all-MiniLM-L6-v2',
      top1_cosine: 0.84,
      gate_runs: [],
      evidence: [
        { id: 'ev-010', cls: 'HELD_OUT_LINES', actor: 'decay', weight: 1, reason: 'Re-verification on disjoint lines failed; demoted.' },
      ],
      ledger: [],
      supersedes: null,
      blind_pending: false,
    },
  ]

  const taxonomy = [
    'stp.portfast.default', 'stp.mode', 'interface.switchport',
    'routing.ospf.passive-interface', 'routing.ospf.area', 'routing.ospf.metric',
    'security.ips.sensor', 'security.av.profile', 'security.waf.profile',
    'mgmt.telnet.enabled', 'mgmt.ssh.v2', 'snmp.community.default',
    'logging.host', 'ntp.server', 'vty.access-class.in',
    'ip.source-route.disabled', 'ip.nd.forward-protocol',
    'ip.directed-broadcast.disabled', 'ip.unreachable.disabled',
    'mgmt.logging.host',
  ]

  const selfaudit = {
    generated_at: '2026-09-29T08:00:00Z',
    seed: 42,
    corpus_sha256: 'sha256:d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5',
    gate_config_hash: 'sha256:1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b',
    model_cards: [
      { role: 'Proposer', name: 'all-MiniLM-L6-v2', family: 'MiniLM', revision: 'abc123' },
      { role: 'Verifier', name: 'cross-encoder/nli-deberta-v3-small', family: 'DeBERTa', revision: 'def456' },
    ],
    stages: {
      regen: {
        false_accept_n: 0, false_accept_rate: 0.000, false_accept_ci: [0.000, 0.021],
        false_reject_n: 2, false_reject_rate: 0.014, false_reject_ci: [0.003, 0.052],
        total: 140,
      },
      lexical: {
        false_accept_n: 3, false_accept_rate: 0.021, false_accept_ci: [0.005, 0.064],
        false_reject_n: 5, false_reject_rate: 0.036, false_reject_ci: [0.013, 0.087],
        total: 140,
      },
      second_model: {
        false_accept_n: 1, false_accept_rate: 0.007, false_accept_ci: [0.001, 0.040],
        false_reject_n: 4, false_reject_rate: 0.029, false_reject_ci: [0.010, 0.075],
        total: 140,
      },
      overall: {
        false_accept_n: 0, false_accept_rate: 0.000, false_accept_ci: [0.000, 0.021],
        false_reject_n: 1, false_reject_rate: 0.007, false_reject_ci: [0.001, 0.040],
        total: 140,
        hard_neg_false_accept: 1, hard_neg_rate: 0.007,
      },
    },
    residual_risk_line: 'a correctly regenerated line assigned to the wrong control can pass all three checks',
    residual_risk_rate: '1/140 = 0.7%',
    residual_risk: `a correctly regenerated line assigned to the wrong control can pass all three checks
Measured rate: 1/140 = 0.7% on the frozen test set (hard negatives). This rate appears here and in every PDF appendix B.
It does not mean the system is broken; it means this risk exists, is measured, and is disclosed (INV-15).`,
  }

  const fixQueue = [
    {
      rank: 1,
      check_id: 'CHK-001',
      title: 'Telnet management access enabled',
      severity: 'CRITICAL',
      severity_weight: 20,
      exploitability: 3.0,
      exploitability_source: 'Known unencrypted interactive credential exposure (Golden Vector B)',
      failing_devices: 3,
      total_evaluated: 5,
      prevalence: 0.60,
      impact: 36.0,
      trust: 'deterministic',
      blast_radius: true,
      blast_note: TELNET_BLAST,
      affected_devices: ['rtr-core-01', 'sw-access-02', 'rtr-edge-03'],
      diffs: {
        'rtr-core-01': `- line vty 0 4\n-  transport input telnet\n+ line vty 0 4\n+  transport input ssh`,
        'sw-access-02': `- transport input all\n+ transport input ssh`,
        'rtr-edge-03': `- line vty 0 15\n-  transport input telnet\n+ line vty 0 15\n+  transport input ssh`,
      },
      before_score: { verified: 71.4, provisional: 74.5, dependence: 25.5 },
      after_by_device: {
        'rtr-core-01': { verified: 82.1, provisional: 84.6, dependence: 18.3, regressions: [] },
        'sw-access-02': {
          verified: 22.9, provisional: 31.4, dependence: 27.7,
          regressions: [{ check_id: 'CHK-010', title: 'SSH version 2 not enforced — newly FAIL after Telnet disable' }],
        },
        'rtr-edge-03': { verified: 77.1, provisional: 79.8, dependence: 21.4, regressions: [] },
      },
    },
    {
      rank: 2,
      check_id: 'CHK-002',
      title: 'Default SNMP community string in use',
      severity: 'CRITICAL',
      severity_weight: 20,
      exploitability: 2.5,
      exploitability_source: 'Public community string brute-force exposure (Golden Vector B)',
      failing_devices: 1,
      total_evaluated: 5,
      prevalence: 0.20,
      impact: 10.0,
      trust: 'deterministic',
      blast_radius: false,
      blast_note: null,
      affected_devices: ['rtr-core-01'],
      diffs: {
        'rtr-core-01': `- snmp-server community public RO\n+ snmp-server community <REDACTED_SECRET> RO 10`,
      },
      before_score: { verified: 71.4, provisional: 74.5, dependence: 25.5 },
      after_by_device: {
        'rtr-core-01': { verified: 77.1, provisional: 79.8, dependence: 22.4, regressions: [] },
      },
    },
    {
      rank: 3,
      check_id: 'CHK-006',
      title: 'HTTP management server active (cleartext)',
      severity: 'HIGH',
      severity_weight: 10,
      exploitability: 1.5,
      exploitability_source: 'Provisional proposal: needs_review: true (exploitability.yaml)',
      failing_devices: 2,
      total_evaluated: 5,
      prevalence: 0.40,
      impact: 6.0,
      trust: 'deterministic',
      blast_radius: false,
      blast_note: null,
      affected_devices: ['sw-access-02', 'fw-perimeter-01'],
      diffs: {
        'sw-access-02': `- ip http server\n+ no ip http server\n+ ip http secure-server`,
        'fw-perimeter-01': `- set system services web-management http\n+ set system services web-management https`,
      },
      before_score: { verified: 65.7, provisional: 69.2, dependence: 27.0 },
      after_by_device: {
        'sw-access-02': { verified: 68.6, provisional: 72.1, dependence: 24.8, regressions: [] },
        'fw-perimeter-01': { verified: 75.2, provisional: 78.4, dependence: 24.1, regressions: [] },
      },
    },
  ]

  const features = {
    test_summary: {
      total_tests: 187,
      passed: 187,
      failed: 0,
      skipped: 16,
      inv_coverage: '100% (17/17 invariants verified for T1 LIVE set)',
      test_suite_run_at: '2026-09-29T10:22:19Z',
      environment: 'pytest-8.1.1 · Python 3.11 · Air-Gapped',
    },
    items: null, // filled by FeatureRegistry from static honest list via API
  }

  return {
    devices,
    signatures,
    mappings,
    taxonomy,
    selfaudit,
    fixQueue,
    features,
    ledger: seedLedger(),
    alerts: [
      {
        id: 'alert-001', type: 'DEMOTION', severity: 'HIGH',
        mapping_id: 'map-003', device: 'fw-edge-01',
        message: 'Mapping map-003 demoted → Demoted after re-verification on held-out lines (INV-06).',
        ts: '2026-09-29T11:22:08Z', acknowledged: false,
      },
    ],
    jobs: {},
    simulations: {},
    lastUploadedDeviceId: null,
    seqCounter: 100,
  }
}

let state = seedState()

export function getState() {
  return state
}

export function resetStore() {
  state = seedState()
  notify()
  return state
}

export function mutate(fn) {
  fn(state)
  notify()
}

export function appendLedger(event, actor, device) {
  const prev = state.ledger.at(-1)?.hash || null
  const seq = state.ledger.length + 1
  const ts = new Date().toISOString()
  const payload = `${seq}|${event}|${actor}|${device}|${ts}|${prev || 'GENESIS'}`
  const entry = { seq, event, actor, device, ts, hash: fullHash(payload), prev_hash: prev, chain_ok: true }
  state.ledger.push(entry)
  return entry
}

export { clone, notify }
