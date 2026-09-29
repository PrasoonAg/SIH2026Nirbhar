"""
parsing.domain.taxonomy — canonical setting_id taxonomy for all four vendors.

Maps vendor-specific config tokens/paths → vendor-neutral setting_id strings.
Used by all parsers to produce Observation objects with pre-resolved setting_id.

§9.2: Seed the taxonomy with ≥ 60 settings across ≥ 10 areas (management, AAA,
SNMP, logging, NTP, banner, secrets, ACL, interface services, routing auth, …)
so top-k ranks and top-3 anchors are meaningful.

INV-04: Known-vendor deterministic lines skip the gate.
"""
from __future__ import annotations

# ─── Canonical setting IDs (≥ 60 settings across 12 areas) ────────────────────

SETTING_IDS = frozenset([
    # --- Area 1: Management plane access ---
    "mgmt.telnet.enabled",          # Telnet management access present
    "mgmt.ssh.v2",                   # SSH forced to version 2
    "mgmt.ssh.timeout",              # SSH connection timeout
    "mgmt.http.server",              # HTTP management interface enabled (cleartext)
    "mgmt.https.server",             # HTTPS management interface enabled (encrypted)
    "mgmt.netconf.enabled",          # NETCONF subsystem active
    "vty.access-class.in",           # Management ACL / permitted-IP / trusted-host
    "vty.exec-timeout",              # Session idle timeout
    "console.exec-timeout",          # Console port idle timeout

    # --- Area 2: AAA (Authentication, Authorization, Accounting) ---
    "aaa.new-model",                 # AAA subsystem enabled globally
    "aaa.authentication.login",      # AAA authentication for interactive logins
    "aaa.authentication.enable",     # AAA authentication for privileged mode
    "aaa.authorization.exec",        # AAA authorization for EXEC shell
    "aaa.authorization.commands",    # AAA authorization for config/commands
    "aaa.accounting.commands",       # AAA command auditing
    "aaa.server.radius",             # RADIUS authentication server configured
    "aaa.server.tacacs",             # TACACS+ authentication server configured

    # --- Area 3: SNMP ---
    "snmp.community.default",        # Default community string (public/private)
    "snmp.configured",               # Any SNMP configuration present
    "snmp.v3.auth-priv",             # SNMPv3 with auth and privacy (encryption)
    "snmp.traps.enabled",            # SNMP security violation traps active
    "snmp.tftp-server.disabled",     # Disallow TFTP uploads via SNMP

    # --- Area 4: Logging & Auditing ---
    "logging.host",                  # Remote syslog server configured
    "logging.trap.level",            # Syslog severity filter (informational or lower)
    "logging.facility",              # Syslog facility code
    "logging.buffered.size",         # In-memory logging buffer configured
    "logging.timestamps.msec",       # Microsecond/millisecond timestamps on logs
    "logging.console.disabled",      # High-rate console logging disabled

    # --- Area 5: NTP & Time Synchronization ---
    "ntp.server",                    # NTP server configured
    "ntp.authenticate",              # NTP cryptographic authentication active
    "ntp.master.disabled",           # Device NTP master clock disabled
    "ntp.timezone",                  # Timezone configured
    "clock.summer-time",             # Daylight saving time adjustment

    # --- Area 6: Warning & Consent Banners ---
    "banner.motd",                   # Message of the Day banner warning
    "banner.login",                  # Pre-login authorization banner
    "banner.exec",                   # Post-login session banner

    # --- Area 7: Secrets & Credential Hygiene ---
    "service.password-encryption",   # Cisco type-7 reversible password masking
    "enable.secret.configured",      # Strong hash for privileged EXEC (type 5/8/9)
    "user.secret.configured",        # Strong hash for local user accounts
    "security.passwords.min-length", # Minimum password length enforced

    # --- Area 8: Access Control Lists (ACLs) ---
    "acl.vty.standard",              # Standard ACL applied to VTY lines
    "acl.control-plane",             # Control plane protection (CoPP) filter
    "acl.management.subnet",         # Dedicated management subnet isolation
    "acl.logging.deny",              # Denied packets logged for auditing

    # --- Area 9: Interface Services & Network Hardening ---
    "ip.redirects.disabled",         # ICMP redirects disabled
    "ip.proxy-arp.disabled",         # Proxy ARP disabled
    "ip.source-route.disabled",      # IP source-route options disabled
    "ip.unreachables.disabled",      # ICMP unreachables disabled to prevent probe
    "ip.mask-reply.disabled",        # ICMP address mask reply disabled
    "ip.gratuitous-arp.disabled",    # Gratuitous ARP disabled

    # --- Area 10: Legacy Risky Services ---
    "service.tcp-small-servers",     # TCP small servers (echo, chargen, etc.)
    "service.udp-small-servers",     # UDP small servers
    "service.finger",                # Finger protocol active
    "service.tcp-keepalives-in",     # TCP keep-alives enabled for incoming sessions
    "service.pad.disabled",          # Packet Assembler/Disassembler disabled
    "service.bootp.disabled",        # BOOTP server disabled

    # --- Area 11: Routing Protocol Security ---
    "routing.bgp.neighbor-auth",     # BGP MD5 neighbor password
    "routing.ospf.message-digest",   # OSPF MD5/SHA authentication
    "routing.rip.auth",              # RIPv2 MD5 authentication
    "routing.isis.auth",             # IS-IS HMAC authentication

    # --- Area 12: Layer 2 / Spanning-Tree Security ---
    "stp.portfast.default",          # PortFast default on access ports
    "stp.bpduguard.default",         # BPDU Guard default enabled
    "stp.bpdufilter.default",        # BPDU Filter default enabled
    "stp.rootguard",                 # Root Guard enabled on edge ports
    "dhcp.snooping.enabled",         # DHCP snooping active
    "arp.inspection.enabled",        # Dynamic ARP inspection (DAI) enabled
])
