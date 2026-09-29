"""
unit/test_fortios_parser.py — golden tests for the FortiOS parser.
"""
from __future__ import annotations

import pytest
from pathlib import Path

from pramana.compliance.domain.engine import ComplianceServiceImpl
from pramana.compliance.domain.seed_checks import SEED_CHECKS_PHASE2
from pramana.compliance.api import FindingStatus
from pramana.parsing.domain.fortios import FortiosParser
from pramana.shared_kernel.api import sha256_bytes

FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "configs" / "fortios"
COMPLIANCE = ComplianceServiceImpl(SEED_CHECKS_PHASE2)


def _parse(filename: str):
    raw = (FIXTURES / filename).read_bytes()
    parser = FortiosParser()
    lines, unrecognized = parser.parse(raw, sha256_bytes(raw))
    return parser.to_normalized_baseline(lines, unrecognized, sha256_bytes(raw))


def _findings(filename: str):
    baseline = _parse(filename)
    return {f.check_id: f for f in COMPLIANCE.evaluate(baseline, f"forti-{filename}", "HEAD")}


# ─── Basic ────────────────────────────────────────────────────────────────────

def test_fortios_parser_produces_observations():
    baseline = _parse("test_findings.cfg")
    assert len(baseline.observations) > 0


def test_fortios_vendor_id():
    baseline = _parse("test_findings.cfg")
    assert baseline.vendor_id == "fortinet_fortios"


# ─── Findings fixture ─────────────────────────────────────────────────────────

@pytest.mark.inv("INV-05")
def test_fortios_findings_chk001_fail():
    """CHK-001: admin-telnet enable → FAIL."""
    m = _findings("test_findings.cfg")
    assert m["CHK-001"].status == FindingStatus.FAIL, "CHK-001 should FAIL (admin-telnet enable)"


@pytest.mark.inv("INV-05")
def test_fortios_findings_chk002_fail():
    """CHK-002: SNMP community name = 'public' → FAIL."""
    m = _findings("test_findings.cfg")
    assert m["CHK-002"].status == FindingStatus.FAIL, "CHK-002 should FAIL (SNMP community public)"


@pytest.mark.inv("INV-05")
def test_fortios_findings_chk004_fail():
    """CHK-004: no syslog configured → FAIL."""
    m = _findings("test_findings.cfg")
    assert m["CHK-004"].status == FindingStatus.FAIL, "CHK-004 should FAIL (no syslog)"


@pytest.mark.inv("INV-05")
def test_fortios_findings_chk005_fail():
    """CHK-005: no NTP configured → FAIL."""
    m = _findings("test_findings.cfg")
    assert m["CHK-005"].status == FindingStatus.FAIL, "CHK-005 should FAIL (no NTP)"


@pytest.mark.inv("INV-05")
def test_fortios_findings_chk006_fail():
    """CHK-006: http in allowaccess → FAIL."""
    m = _findings("test_findings.cfg")
    assert m["CHK-006"].status == FindingStatus.FAIL, "CHK-006 should FAIL (HTTP in allowaccess)"


# ─── Clean fixture ────────────────────────────────────────────────────────────

@pytest.mark.inv("INV-05")
def test_fortios_clean_chk001_pass():
    m = _findings("test_clean.cfg")
    assert m["CHK-001"].status == FindingStatus.PASS, "CHK-001 should PASS (admin-telnet disable)"


@pytest.mark.inv("INV-05")
def test_fortios_clean_chk002_pass():
    m = _findings("test_clean.cfg")
    assert m["CHK-002"].status == FindingStatus.PASS, "CHK-002 should PASS (non-default community)"


@pytest.mark.inv("INV-05")
def test_fortios_clean_chk004_pass():
    m = _findings("test_clean.cfg")
    assert m["CHK-004"].status == FindingStatus.PASS, "CHK-004 should PASS (syslog configured)"


@pytest.mark.inv("INV-05")
def test_fortios_clean_chk005_pass():
    m = _findings("test_clean.cfg")
    assert m["CHK-005"].status == FindingStatus.PASS, "CHK-005 should PASS (NTP configured)"


@pytest.mark.inv("INV-05")
def test_fortios_clean_chk006_pass():
    m = _findings("test_clean.cfg")
    assert m["CHK-006"].status == FindingStatus.PASS, "CHK-006 should PASS (no http in allowaccess)"


@pytest.mark.inv("INV-08")
def test_fortios_findings_carry_trust():
    for f in COMPLIANCE.evaluate(_parse("test_findings.cfg"), "forti-x", "HEAD"):
        assert f.trust


@pytest.mark.inv("INV-13")
def test_fortios_parse_deterministic():
    raw = (FIXTURES / "test_findings.cfg").read_bytes()
    sha = sha256_bytes(raw)
    parser = FortiosParser()
    l1, _ = parser.parse(raw, sha)
    l2, _ = parser.parse(raw, sha)
    assert [l.tokens for l in l1] == [l.tokens for l in l2]
