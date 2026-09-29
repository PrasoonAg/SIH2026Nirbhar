"""
shared_kernel.redactor — Secret hygiene (INV-16).

Pure functional. Redacts secrets from strings, dicts, and logs.

Rules:
- SNMP community strings: redact all EXCEPT 'public' and 'private'
  (which are themselves findings and must be visible).
- Passwords: always redact (enable secret, set password, set admin-password, etc.).
- BGP MD5 keys, RADIUS/TACACS keys: always redact.
- Certificate/key material: always redact.
- Well-known defaults (public, private) are NEVER redacted (INV-16 exception).

Redaction marker: '<REDACTED>' (uppercase, bracketed, never confusable with a real value).

This module MUST NOT import from compliance, pipeline, ingest, reporting, or
trustgate (only shared_kernel). It is a pure utility.
"""
from __future__ import annotations

import re
from typing import Any


# ─── Sentinel ────────────────────────────────────────────────────────────────

REDACTED = "<REDACTED>"

# ─── Allowlist: values that are findings and must stay visible ────────────────

_SNMP_FINDINGS = frozenset(["public", "private"])

# ─── Line-level redaction patterns ───────────────────────────────────────────
# Each tuple: (label, compiled pattern, replacement template)
# Patterns use named group 'secret' to capture the value to redact.

_REDACT_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    # Cisco: enable secret / enable password
    (
        "cisco_enable_secret",
        re.compile(r"(?i)^(enable\s+(?:secret|password)\s+(?:\d+\s+)?)\S+"),
        lambda m: m.group(0)[: m.start(0)] + m.group(1) + REDACTED,
    ),
    # Cisco: username X password/secret Y
    (
        "cisco_username",
        re.compile(r"(?i)^(username\s+\S+\s+(?:password|secret)\s+(?:\d+\s+)?)(\S+)"),
        lambda m: m.group(1) + REDACTED,
    ),
    # Cisco: SNMP community (non-default)
    (
        "cisco_snmp_community",
        re.compile(r"(?i)^(snmp-server\s+community\s+)(\S+)(.*)$"),
        lambda m: m.group(1) + (_snmp_value(m.group(2))) + m.group(3),
    ),
    # Cisco/JunOS: RADIUS / TACACS / BGP MD5 key
    (
        "cisco_radius_key",
        re.compile(r"(?i)^(\s*(?:authentication-)?key\s+(?:\d+\s+)?)\S+"),
        lambda m: m.group(1) + REDACTED,
    ),
    # JunOS: password/secret in any position (full remaining line redacted)
    (
        "junos_password",
        re.compile(r"(?i)((?:plaintext-)?password|secret|plaintext-password)\s+(\S+)"),
        lambda m: m.group(1) + " " + REDACTED,
    ),
    # JunOS: SNMP community (non-default)
    (
        "junos_snmp_community",
        re.compile(r"(?i)(community\s+)(\S+)"),
        lambda m: m.group(1) + _snmp_value(m.group(2)),
    ),
    # FortiOS: set password / set passwd / set key (full value redaction)
    (
        "fortios_password",
        re.compile(r"(?i)^(\s*set\s+(?:password|passwd|psksecret|key)\s+)(.+)$"),
        lambda m: m.group(1) + REDACTED,
    ),
    # FortiOS: encrypted password blocks (ENC AAAA...)
    (
        "fortios_enc",
        re.compile(r"(?i)(ENC\s+)\S+"),
        lambda m: m.group(1) + REDACTED,
    ),
    # Generic: certificate / PEM key material
    (
        "pem_key",
        re.compile(r"-----BEGIN [A-Z ]+-----.*?-----END [A-Z ]+-----", re.DOTALL),
        lambda m: REDACTED,
    ),
    # PAN-OS: phash / password in XML
    (
        "panos_password",
        re.compile(r"(?i)(<(?:phash|password|secret|key|api-key)>)(.*?)(</[^>]+>)"),
        lambda m: m.group(1) + REDACTED + m.group(3),
    ),
]


def _snmp_value(community: str) -> str:
    """Return community unchanged if it's a finding value; redact otherwise."""
    if community.lower() in _SNMP_FINDINGS:
        return community  # Keep — it IS the finding
    return REDACTED


# ─── Public API ───────────────────────────────────────────────────────────────

def redact_line(line: str) -> str:
    """
    Apply all redaction patterns to a single config line.
    Returns the redacted line. Pure function.
    """
    for _label, pattern, replacer in _REDACT_PATTERNS:
        line = pattern.sub(replacer, line)
    return line


def redact_text(text: str) -> str:
    """
    Redact all secrets in a multi-line config text.
    Pure function. INV-16.
    """
    return "\n".join(redact_line(line) for line in text.splitlines())


def redact_dict(data: Any, *, _depth: int = 0) -> Any:
    """
    Recursively redact secrets in a nested dict / list / str.
    Used before sending data to logs, Ollama, or PDF rendering.
    Max recursion depth: 50 (prevents pathological inputs).
    """
    if _depth > 50:
        return REDACTED
    if isinstance(data, str):
        return redact_line(data)
    if isinstance(data, dict):
        return {k: redact_dict(v, _depth=_depth + 1) for k, v in data.items()}
    if isinstance(data, (list, tuple)):
        redacted = [redact_dict(item, _depth=_depth + 1) for item in data]
        return type(data)(redacted)
    return data


def is_redacted(value: str) -> bool:
    """Return True if the value is the redaction sentinel."""
    return value == REDACTED
