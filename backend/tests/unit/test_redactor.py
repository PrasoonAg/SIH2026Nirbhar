"""
unit/test_redactor.py — property and unit tests for the Redactor (INV-16).
"""
from __future__ import annotations

import pytest
from pramana.shared_kernel.redactor import (
    REDACTED,
    is_redacted,
    redact_dict,
    redact_line,
    redact_text,
)


# ─── Basic redaction ─────────────────────────────────────────────────────────

@pytest.mark.inv("INV-16")
def test_cisco_enable_secret_redacted():
    line = "enable secret 5 $1$mERr$hx5rVt7rPNoS4wqbXKX7m0"
    result = redact_line(line)
    assert REDACTED in result
    assert "$1$mERr$hx5rVt7rPNoS4wqbXKX7m0" not in result


@pytest.mark.inv("INV-16")
def test_cisco_enable_password_redacted():
    result = redact_line("enable password cisco123")
    assert REDACTED in result
    assert "cisco123" not in result


@pytest.mark.inv("INV-16")
def test_cisco_username_secret_redacted():
    result = redact_line("username admin secret 5 $1$abc$def")
    assert REDACTED in result
    assert "$1$abc$def" not in result


@pytest.mark.inv("INV-16")
def test_cisco_snmp_non_default_redacted():
    """Non-default SNMP community must be redacted."""
    result = redact_line("snmp-server community NTRO-SECRET-RO RO")
    assert REDACTED in result
    assert "NTRO-SECRET-RO" not in result


@pytest.mark.inv("INV-16")
def test_cisco_snmp_public_not_redacted():
    """'public' SNMP community must NOT be redacted — it IS the finding."""
    result = redact_line("snmp-server community public RO")
    assert "public" in result
    assert REDACTED not in result


@pytest.mark.inv("INV-16")
def test_cisco_snmp_private_not_redacted():
    """'private' SNMP community must NOT be redacted — it IS the finding."""
    result = redact_line("snmp-server community private RW")
    assert "private" in result
    assert REDACTED not in result


@pytest.mark.inv("INV-16")
def test_fortios_password_redacted():
    result = redact_line("    set password ENC AAAA1234BBBB5678")
    assert REDACTED in result
    assert "AAAA1234BBBB5678" not in result


@pytest.mark.inv("INV-16")
def test_fortios_enc_redacted():
    result = redact_line("        set password ENC SeCrEtStRiNg123!")
    assert REDACTED in result


@pytest.mark.inv("INV-16")
def test_junos_password_redacted():
    # JunOS authentication-key or password lines
    result = redact_line("    authentication-key MyP@ssw0rd")
    assert REDACTED in result or "MyP@ssw0rd" not in result

    # JunOS set password (actual syntax in authentication stanzas)
    result2 = redact_line("    password MyP@ssw0rd;")
    assert REDACTED in result2
    assert "MyP@ssw0rd" not in result2


@pytest.mark.inv("INV-16")
def test_panos_phash_redacted():
    result = redact_line("<phash>$6$abcdef123456/hash</phash>")
    assert REDACTED in result
    assert "$6$abcdef123456/hash" not in result


# ─── Multi-line text redaction ────────────────────────────────────────────────

@pytest.mark.inv("INV-16")
def test_redact_text_multi_line():
    text = (
        "hostname router\n"
        "enable secret 5 $1$mERr$hx5rVt7rPNoS4wqbXKX7m0\n"
        "snmp-server community public RO\n"
        "snmp-server community NTRO-SECRET RO\n"
    )
    result = redact_text(text)
    assert "hostname router" in result
    assert "$1$mERr$hx5rVt7rPNoS4wqbXKX7m0" not in result
    assert "public" in result          # kept — it's a finding
    assert "NTRO-SECRET" not in result  # redacted — non-default


# ─── Dict redaction ───────────────────────────────────────────────────────────

@pytest.mark.inv("INV-16")
def test_redact_dict_nested():
    data = {
        "hostname": "router-01",
        "config": {
            "line": "enable secret 5 $1$mERr$hx5rVt7rPNoS4wqbXKX7m0",
            "nested": ["snmp-server community public RO"],
        },
    }
    result = redact_dict(data)
    assert result["hostname"] == "router-01"
    assert "$1$mERr$hx5rVt7rPNoS4wqbXKX7m0" not in str(result)
    assert "public" in str(result)


@pytest.mark.inv("INV-16")
def test_redact_dict_max_depth():
    """Pathologically deep dicts must not stack-overflow."""
    deep: dict = {}
    node = deep
    for _ in range(60):
        node["a"] = {}
        node = node["a"]
    node["val"] = "safe"
    # Should not raise
    result = redact_dict(deep)
    assert result is not None


# ─── Sentinel ─────────────────────────────────────────────────────────────────

def test_is_redacted_true():
    assert is_redacted(REDACTED)


def test_is_redacted_false():
    assert not is_redacted("not-redacted")
    assert not is_redacted("public")


# ─── Idempotency ─────────────────────────────────────────────────────────────

@pytest.mark.inv("INV-16")
def test_redact_line_idempotent():
    """Redacting an already-redacted line produces the same result."""
    line = "enable secret 5 $1$abc$def"
    once = redact_line(line)
    twice = redact_line(once)
    assert once == twice


# ─── Non-secret lines pass through unchanged ─────────────────────────────────

def test_non_secret_lines_unchanged():
    safe_lines = [
        "hostname router-01",
        "interface GigabitEthernet0/0",
        "ip address 10.0.0.1 255.255.255.0",
        "ntp server 10.0.100.10",
        "logging host 10.0.100.5",
        "transport input ssh",
    ]
    for line in safe_lines:
        assert redact_line(line) == line, f"Non-secret line was modified: {line!r}"
