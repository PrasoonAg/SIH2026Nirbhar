"""
proposer.domain.anchors — Anchors catalog and deterministic cosine similarity (§9.2).

Seed anchors across settings. Deterministic cosine similarity (CPU-only, no egress).
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Sequence

# ─── Seed Anchors (§9.2) ───────────────────────────────────────────────────────
SEED_ANCHORS: tuple[tuple[str, str], ...] = (
    # Spanning-Tree
    ("stp.portfast.default", "Enable PortFast globally on access ports"),
    ("stp.portfast.default", "spanning-tree portfast default edge access"),
    ("stp.bpduguard.default", "Enable Spanning Tree BPDU Guard globally"),
    ("stp.bpduguard.default", "spanning-tree portfast bpduguard default"),
    ("stp.bpdufilter.default", "spanning-tree portfast bpdufilter default"),
    ("stp.rootguard", "spanning-tree guard root on designated port"),

    # Management Access
    ("mgmt.telnet.enabled", "Enable Telnet remote terminal access transport input telnet"),
    ("mgmt.telnet.enabled", "transport input telnet on vty terminal line"),
    ("mgmt.ssh.v2", "Force SSH protocol version 2 ip ssh version 2"),
    ("mgmt.ssh.v2", "set system services ssh protocol-version v2"),
    ("mgmt.http.server", "Enable HTTP cleartext management web interface ip http server"),
    ("mgmt.https.server", "Enable HTTPS secure web management ip http secure-server"),
    ("vty.access-class.in", "Restrict VTY line management access using access-class or ACL"),
    ("vty.exec-timeout", "Set executive session idle timeout exec-timeout on vty lines"),

    # AAA
    ("aaa.new-model", "Enable global AAA subsystem aaa new-model"),
    ("aaa.authentication.login", "Configure AAA authentication login default group tacacs"),
    ("aaa.server.radius", "radius-server host authentication accounting server"),
    ("aaa.server.tacacs", "tacacs-server host authentication accounting server"),

    # SNMP
    ("snmp.community.default", "Configure SNMP default community string public private"),
    ("snmp.community.default", "snmp-server community public RO"),
    ("snmp.v3.auth-priv", "snmp-server group v3 priv auth sha aes"),

    # Logging
    ("logging.host", "Configure remote syslog logging host server ip"),
    ("logging.host", "logging host remote syslog server"),
    ("logging.timestamps.msec", "service timestamps log datetime msec"),

    # NTP
    ("ntp.server", "Configure network time protocol NTP server ip address"),
    ("ntp.server", "ntp server synchronized clock source"),
    ("ntp.authenticate", "ntp authenticate trusted-key"),

    # Passwords & Secrets
    ("service.password-encryption", "Enable service password-encryption for weak hash masking"),
    ("enable.secret.configured", "enable secret privileged execution password"),
    ("user.secret.configured", "username admin secret privileged password"),

    # Risky Services
    ("service.finger", "service finger protocol active ip finger"),
    ("service.tcp-small-servers", "service tcp-small-servers echo discard chargen"),
    ("service.udp-small-servers", "service udp-small-servers echo discard chargen"),

    # Network Hardening
    ("ip.redirects.disabled", "no ip redirects on interfaces"),
    ("ip.proxy-arp.disabled", "no ip proxy-arp on interfaces"),
    ("ip.source-route.disabled", "no ip source-route options processing"),
)


def _tokenize(text: str) -> list[str]:
    """Tokenize into lowercase words and character n-grams for robust matching."""
    words = re.findall(r"[a-z0-9_.-]+", text.lower())
    ngrams: list[str] = list(words)
    # Character 3-grams for vocabulary overlap
    for w in words:
        if len(w) >= 3:
            for i in range(len(w) - 2):
                ngrams.append(w[i:i+3])
    return ngrams


def compute_cosine(vec_a: Counter[str], vec_b: Counter[str]) -> float:
    """Compute cosine similarity between two token frequency vectors."""
    intersection = set(vec_a.keys()) & set(vec_b.keys())
    numerator = sum(vec_a[x] * vec_b[x] for x in intersection)

    sum_a = sum(v ** 2 for v in vec_a.values())
    sum_b = sum(v ** 2 for v in vec_b.values())
    denominator = math.sqrt(sum_a) * math.sqrt(sum_b)

    if not denominator:
        return 0.0
    return float(numerator) / denominator


def rank_anchors(
    line_text: str,
    anchors: Sequence[tuple[str, str]] = SEED_ANCHORS,
    top_k: int = 3,
) -> list[tuple[str, str, float]]:
    """
    Rank anchor phrases against a line and return top-k matches with cosine scores.
    Deduplicates by setting_id, keeping the highest cosine per setting.
    """
    line_vec = Counter(_tokenize(line_text))
    scores: dict[str, tuple[str, float]] = {}

    for setting_id, phrase in anchors:
        phrase_vec = Counter(_tokenize(phrase))
        sim = compute_cosine(line_vec, phrase_vec)

        # Baseline bonus for exact keyword matches
        line_lower = line_text.lower()
        if any(part in line_lower for part in setting_id.split(".")):
            sim = min(1.0, sim + 0.15)

        if setting_id not in scores or sim > scores[setting_id][1]:
            scores[setting_id] = (phrase, round(sim, 3))

    sorted_candidates = sorted(
        [(sid, phrase, cos) for sid, (phrase, cos) in scores.items()],
        key=lambda x: x[2],
        reverse=True,
    )

    return sorted_candidates[:top_k]
