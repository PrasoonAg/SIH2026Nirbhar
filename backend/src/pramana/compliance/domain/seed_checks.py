"""
compliance.domain.seed_checks — Phase 2 seed check catalog.

10 checks × 4 vendors (Cisco IOS, JunOS, PAN-OS, FortiOS).
All predicates use canonical setting_id values from parsing.domain.taxonomy.

source: §8 + Vernils.pdf + CIS Benchmarks (paraphrase; verified: false).
A11: Exploitability multipliers other than Telnet 3.0 and default SNMP 2.5 are flagged.
"""
from __future__ import annotations

from pramana.compliance.api import BlastRadiusRule, Check, FrameworkRef, Framework
from pramana.shared_kernel.api import Severity

# ─── Framework references (paraphrase only — verified: false) ─────────────────

_NIST_IAC = FrameworkRef(
    framework=Framework.NIST,
    control_id="AC-17",
    title="Remote Access",
    required_state="absent",
    source="NIST SP 800-53 Rev5",
    source_version="Rev5",
    verified=False,
)
_CIS_MGMT = FrameworkRef(
    framework=Framework.CIS,
    control_id="CIS-12.1",
    title="Ensure management access uses encrypted protocols",
    required_state="absent",
    source="CIS Benchmarks (paraphrase)",
    source_version="v4.0",
    verified=False,
)
_NIST_SI = FrameworkRef(
    framework=Framework.NIST,
    control_id="SI-2",
    title="Flaw Remediation",
    required_state="configured",
    source="NIST SP 800-53 Rev5",
    source_version="Rev5",
    verified=False,
)
_CIS_SNMP = FrameworkRef(
    framework=Framework.CIS,
    control_id="CIS-12.3",
    title="Ensure SNMP uses non-default community strings",
    required_state="absent",
    source="CIS Benchmarks (paraphrase)",
    source_version="v4.0",
    verified=False,
)
_NIST_AU = FrameworkRef(
    framework=Framework.NIST,
    control_id="AU-9",
    title="Protection of Audit Information",
    required_state="configured",
    source="NIST SP 800-53 Rev5",
    source_version="Rev5",
    verified=False,
)
_NIST_SC = FrameworkRef(
    framework=Framework.NIST,
    control_id="SC-8",
    title="Transmission Confidentiality and Integrity",
    required_state="configured",
    source="NIST SP 800-53 Rev5",
    source_version="Rev5",
    verified=False,
)

# ─── Blast radius rules ───────────────────────────────────────────────────────

_BLAST_SESSION = BlastRadiusRule(
    category="session",
    level="HIGH",
    note="Disabling telnet terminates all active in-band telnet management sessions.",
)
_BLAST_SNMP = BlastRadiusRule(
    category="monitoring",
    level="MEDIUM",
    note="Removing SNMP community breaks NMS polling until new community is configured.",
)
_BLAST_ACL = BlastRadiusRule(
    category="acl",
    level="HIGH",
    note="Adding management ACL may lock out remote admin sessions; test from console.",
)
_BLAST_LOW = BlastRadiusRule(
    category="service",
    level="LOW",
    note="Disabling legacy service has minimal operational impact on modern networks.",
)

# ─── Seed checks ──────────────────────────────────────────────────────────────

SEED_CHECKS_PHASE2: list[Check] = [

    # CHK-001: Telnet management access
    # PASS = telnet is absent (device is compliant).
    # FAIL = telnet is present (device has the vulnerability).
    Check(
        check_id="CHK-001",
        title="Telnet management access enabled",
        severity=Severity.CRITICAL,
        predicate={
            "not": {"setting": "mgmt.telnet.enabled", "op": "present"}
        },
        evidence_selector={"lines_matching": "transport input telnet|set system services telnet|telnet.*yes|admin-telnet.*enable"},
        remediation={
            "cisco_ios": {
                "diff": "- transport input telnet ssh\n+ transport input ssh\n",
                "rationale": "Remove telnet from allowed transport protocols on VTY lines.",
            },
            "juniper_junos": {
                "diff": "- set system services telnet\n",
                "rationale": "Delete the telnet service stanza from system services.",
            },
            "palo_alto_panos": {
                "diff": "- <telnet>yes</telnet>\n+ <telnet>no</telnet>\n",
                "rationale": "Set telnet to no in the interface management profile.",
            },
            "fortinet_fortios": {
                "diff": "- set admin-telnet enable\n+ set admin-telnet disable\n",
                "rationale": "Disable telnet in config system global.",
            },
        },
        blast_radius=(
            BlastRadiusRule(
                category="session",
                level="HIGH",
                note="Active telnet management sessions will be terminated immediately.",
            ),
        ),
        framework_refs=(_NIST_IAC, _CIS_MGMT),
    ),

    # CHK-002: Default SNMP community strings
    # PASS = no default communities (public/private) present.
    Check(
        check_id="CHK-002",
        title="Default SNMP community string in use",
        severity=Severity.CRITICAL,
        predicate={
            "not": {"setting": "snmp.community.default", "op": "present"}
        },
        evidence_selector={"lines_matching": "community (public|private)"},
        remediation={
            "cisco_ios": {
                "diff": "- snmp-server community public RO\n- snmp-server community private RW\n+ snmp-server community <NTRO-RO-STRING> RO <ACL-NAME>\n",
                "rationale": "Replace default community strings with site-specific values scoped to an ACL.",
            },
            "juniper_junos": {
                "diff": "- set snmp community public authorization read-only\n- set snmp community private authorization read-write\n+ set snmp community <NTRO-RO-STRING> authorization read-only clients 10.0.0.0/8\n",
                "rationale": "Remove default communities; add site-specific community with client restriction.",
            },
            "palo_alto_panos": {
                "diff": "- <snmp-community-string>public</snmp-community-string>\n+ <snmp-community-string><NTRO-RO-STRING></snmp-community-string>\n",
                "rationale": "Replace default SNMP community with site-specific string.",
            },
            "fortinet_fortios": {
                "diff": "- set name public\n+ set name <NTRO-RO-STRING>\n",
                "rationale": "Rename default SNMP community to a site-specific value and restrict hosts.",
            },
        },
        blast_radius=(_BLAST_SNMP,),
        framework_refs=(_CIS_SNMP, _NIST_SI),
    ),

    # CHK-003: VTY / management interface ACL
    # PASS = management ACL / permitted-IP / trusted-host is configured.
    Check(
        check_id="CHK-003",
        title="Management access not restricted by ACL / permitted-IP",
        severity=Severity.HIGH,
        predicate={"setting": "vty.access-class.in", "op": "present"},
        evidence_selector={"lines_matching": "access-class.*in|permitted-ip|trusted-hosts"},
        remediation={
            "cisco_ios": {
                "diff": "+ access-class MGMT-ACCESS in\n",
                "rationale": "Apply an inbound access-class to all VTY lines to restrict management source IPs.",
            },
            "juniper_junos": {
                "diff": "+ set firewall filter MGMT-ACCESS term permit-mgmt from source-address 10.0.0.0/8\n+ set interfaces fxp0 unit 0 family inet filter input MGMT-ACCESS\n",
                "rationale": "Apply a firewall filter to the management interface.",
            },
            "palo_alto_panos": {
                "diff": "+ <permitted-ip><entry name='mgmt-subnet'><ip-netmask>10.0.0.0/8</ip-netmask></entry></permitted-ip>\n",
                "rationale": "Configure permitted-ip under system to restrict management access.",
            },
            "fortinet_fortios": {
                "diff": "+ set trusted-hosts 10.0.0.0 255.0.0.0\n",
                "rationale": "Set trusted-hosts in admin account to restrict management source IPs.",
            },
        },
        blast_radius=(_BLAST_ACL,),
        framework_refs=(_NIST_IAC, _CIS_MGMT),
    ),

    # CHK-004: Remote syslog configured
    # PASS = logging.host is present.
    Check(
        check_id="CHK-004",
        title="Remote syslog not configured",
        severity=Severity.HIGH,
        predicate={"setting": "logging.host", "op": "present"},
        evidence_selector={"lines_matching": "logging host|set system syslog host|<syslog>|config log syslogd"},
        remediation={
            "cisco_ios": {
                "diff": "+ logging host 10.0.100.5\n+ logging trap informational\n",
                "rationale": "Configure a remote syslog server for audit trail centralisation.",
            },
            "juniper_junos": {
                "diff": "+ set system syslog host 10.0.100.5 any any\n",
                "rationale": "Add a remote syslog host under system syslog.",
            },
            "palo_alto_panos": {
                "diff": "+ <syslog><entry name='syslog-server'><server>10.0.100.5</server></entry></syslog>\n",
                "rationale": "Configure a syslog server profile and reference it in the log forwarding profile.",
            },
            "fortinet_fortios": {
                "diff": "+ config log syslogd setting\n+     set status enable\n+     set server 10.0.100.5\n+ end\n",
                "rationale": "Enable syslog forwarding in config log syslogd setting.",
            },
        },
        blast_radius=(),
        framework_refs=(_NIST_AU,),
    ),

    # CHK-005: NTP configured
    # PASS = ntp.server is present.
    Check(
        check_id="CHK-005",
        title="NTP not configured",
        severity=Severity.MEDIUM,
        predicate={"setting": "ntp.server", "op": "present"},
        evidence_selector={"lines_matching": "ntp server|set system ntp|ntp-server-address|config system ntp"},
        remediation={
            "cisco_ios": {
                "diff": "+ ntp server 10.0.100.10\n+ ntp server 10.0.100.11\n",
                "rationale": "Configure NTP servers to ensure accurate log timestamps (INV-13).",
            },
            "juniper_junos": {
                "diff": "+ set system ntp server 10.0.100.10\n",
                "rationale": "Configure NTP under system ntp.",
            },
            "palo_alto_panos": {
                "diff": "+ <ntp-servers><primary-ntp-server><ntp-server-address>10.0.100.10</ntp-server-address></primary-ntp-server></ntp-servers>\n",
                "rationale": "Configure primary and secondary NTP servers under deviceconfig system.",
            },
            "fortinet_fortios": {
                "diff": "+ config system ntp\n+     set ntpsync enable\n+     config ntpserver\n+         edit 1\n+             set server 10.0.100.10\n+         next\n+     end\n+ end\n",
                "rationale": "Enable NTP synchronisation under config system ntp.",
            },
        },
        blast_radius=(),
        framework_refs=(_NIST_AU,),
    ),

    # CHK-006: HTTP management server enabled (cleartext)
    # PASS = mgmt.http.server is absent.
    Check(
        check_id="CHK-006",
        title="HTTP management server enabled (cleartext)",
        severity=Severity.HIGH,
        predicate={
            "not": {"setting": "mgmt.http.server", "op": "present"}
        },
        evidence_selector={"lines_matching": "ip http server|web-management http|<http>yes|allowaccess.*http"},
        remediation={
            "cisco_ios": {
                "diff": "- ip http server\n+ ip http secure-server\n+ no ip http server\n",
                "rationale": "Disable cleartext HTTP management; enable HTTPS only.",
            },
            "juniper_junos": {
                "diff": "- set system services web-management http interface fxp0.0\n+ set system services web-management https interface fxp0.0\n",
                "rationale": "Replace HTTP web-management with HTTPS.",
            },
            "palo_alto_panos": {
                "diff": "- <http>yes</http>\n+ <http>no</http>\n+ <https>yes</https>\n",
                "rationale": "Disable HTTP in management profile; use HTTPS only.",
            },
            "fortinet_fortios": {
                "diff": "- set allowaccess https ssh http ping\n+ set allowaccess https ssh ping\n",
                "rationale": "Remove http from allowaccess on the management interface.",
            },
        },
        blast_radius=(
            BlastRadiusRule(
                category="session",
                level="MEDIUM",
                note="HTTP management GUI sessions will be terminated; HTTPS only.",
            ),
        ),
        framework_refs=(_NIST_SC, _CIS_MGMT),
    ),

    # CHK-007: TCP small servers
    # PASS = service.tcp-small-servers is absent (no explicit enable line).
    Check(
        check_id="CHK-007",
        title="TCP small servers enabled (echo/chargen/discard/daytime)",
        severity=Severity.MEDIUM,
        predicate={
            "not": {"setting": "service.tcp-small-servers", "op": "present"}
        },
        evidence_selector={"lines_matching": "service tcp-small-servers"},
        remediation={
            "cisco_ios": {
                "diff": "- service tcp-small-servers\n+ no service tcp-small-servers\n",
                "rationale": "Disable legacy TCP small servers — not needed on modern devices.",
            },
        },
        blast_radius=(_BLAST_LOW,),
        framework_refs=(_NIST_SI,),
    ),

    # CHK-008: UDP small servers
    # PASS = service.udp-small-servers is absent.
    Check(
        check_id="CHK-008",
        title="UDP small servers enabled (echo/chargen/discard/daytime)",
        severity=Severity.MEDIUM,
        predicate={
            "not": {"setting": "service.udp-small-servers", "op": "present"}
        },
        evidence_selector={"lines_matching": "service udp-small-servers"},
        remediation={
            "cisco_ios": {
                "diff": "- service udp-small-servers\n+ no service udp-small-servers\n",
                "rationale": "Disable legacy UDP small servers.",
            },
        },
        blast_radius=(_BLAST_LOW,),
        framework_refs=(_NIST_SI,),
    ),

    # CHK-009: Finger service
    # PASS = service.finger is absent.
    Check(
        check_id="CHK-009",
        title="Finger service enabled (user information disclosure)",
        severity=Severity.LOW,
        predicate={
            "not": {"setting": "service.finger", "op": "present"}
        },
        evidence_selector={"lines_matching": "service finger|ip finger"},
        remediation={
            "cisco_ios": {
                "diff": "- service finger\n+ no service finger\n",
                "rationale": "Disable finger service to prevent unauthenticated user enumeration.",
            },
        },
        blast_radius=(_BLAST_LOW,),
        framework_refs=(_NIST_SI,),
    ),

    # CHK-010: SSH version 2 enforced
    # PASS = mgmt.ssh.v2 is present (version 2 forced).
    Check(
        check_id="CHK-010",
        title="SSH version 2 not enforced (SSHv1 permitted)",
        severity=Severity.HIGH,
        predicate={"setting": "mgmt.ssh.v2", "op": "present"},
        evidence_selector={"lines_matching": "ip ssh version 2|ssh protocol-version v2|admin-ssh-v1"},
        remediation={
            "cisco_ios": {
                "diff": "+ ip ssh version 2\n",
                "rationale": "Force SSH version 2; SSHv1 is deprecated and vulnerable.",
            },
            "juniper_junos": {
                "diff": "+ set system services ssh protocol-version v2\n",
                "rationale": "Restrict SSH to protocol-version v2 under system services ssh.",
            },
            "palo_alto_panos": {
                "diff": "# PAN-OS defaults to SSHv2; verify in system ssh settings.\n",
                "rationale": "PAN-OS defaults to SSHv2; verify explicit configuration if available.",
            },
            "fortinet_fortios": {
                "diff": "+ config system global\n+     set admin-ssh-v1 disable\n+ end\n",
                "rationale": "Disable SSH version 1 in config system global.",
            },
        },
        blast_radius=(_BLAST_LOW,),
        framework_refs=(_NIST_SC, _CIS_MGMT),
    ),
]

# ─── Phase 1 compatibility alias ─────────────────────────────────────────────
# The first 3 checks are used in Phase 1 tests; this alias keeps them working.
SEED_CHECKS_PHASE1 = SEED_CHECKS_PHASE2[:3]
