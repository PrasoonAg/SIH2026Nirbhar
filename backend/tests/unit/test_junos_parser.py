"""
unit/test_junos_parser.py — golden tests for the JunOS parser.
"""
from __future__ import annotations

import pytest
from pathlib import Path

from pramana.compliance.domain.engine import ComplianceServiceImpl
from pramana.compliance.domain.seed_checks import SEED_CHECKS_PHASE2
from pramana.compliance.api import FindingStatus
from pramana.parsing.domain.junos import JunosParser
from pramana.shared_kernel.api import sha256_bytes

FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "configs" / "junos"
CHECKS = SEED_CHECKS_PHASE2
COMPLIANCE = ComplianceServiceImpl(CHECKS)


def _parse(filename: str):
    raw = (FIXTURES / filename).read_bytes()
    parser = JunosParser()
    lines, unrecognized = parser.parse(raw, sha256_bytes(raw))
    baseline = parser.to_normalized_baseline(lines, unrecognized, sha256_bytes(raw))
    return baseline


def _findings(filename: str):
    baseline = _parse(filename)
    findings = COMPLIANCE.evaluate(baseline, f"junos-{filename}", "HEAD")
    return {f.check_id: f for f in findings}


# ─── Vendor detection ─────────────────────────────────────────────────────────

def test_junos_parser_produces_observations():
    baseline = _parse("test_findings.cfg")
    assert len(baseline.observations) > 0


def test_junos_parser_vendor_id():
    baseline = _parse("test_findings.cfg")
    assert baseline.vendor_id == "juniper_junos"


# ─── Findings fixture (all violations) ───────────────────────────────────────

@pytest.mark.inv("INV-05")
def test_junos_findings_chk001_fail():
    """CHK-001: telnet stanza present → FAIL."""
    m = _findings("test_findings.cfg")
    assert m["CHK-001"].status == FindingStatus.FAIL, "CHK-001 should FAIL (telnet in services)"


@pytest.mark.inv("INV-05")
def test_junos_findings_chk002_fail():
    """CHK-002: public + private communities → FAIL."""
    m = _findings("test_findings.cfg")
    assert m["CHK-002"].status == FindingStatus.FAIL, "CHK-002 should FAIL (default SNMP community)"


@pytest.mark.inv("INV-05")
def test_junos_findings_chk004_fail():
    """CHK-004: no remote syslog → FAIL."""
    m = _findings("test_findings.cfg")
    assert m["CHK-004"].status == FindingStatus.FAIL, "CHK-004 should FAIL (no syslog host)"


@pytest.mark.inv("INV-05")
def test_junos_findings_chk005_fail():
    """CHK-005: no NTP → FAIL."""
    m = _findings("test_findings.cfg")
    assert m["CHK-005"].status == FindingStatus.FAIL, "CHK-005 should FAIL (no NTP)"


@pytest.mark.inv("INV-05")
def test_junos_findings_chk006_fail():
    """CHK-006: web-management http present → FAIL."""
    m = _findings("test_findings.cfg")
    assert m["CHK-006"].status == FindingStatus.FAIL, "CHK-006 should FAIL (HTTP management)"


# ─── Clean fixture (all pass) ─────────────────────────────────────────────────

@pytest.mark.inv("INV-05")
def test_junos_clean_chk001_pass():
    m = _findings("test_clean.cfg")
    assert m["CHK-001"].status == FindingStatus.PASS, "CHK-001 should PASS (no telnet)"


@pytest.mark.inv("INV-05")
def test_junos_clean_chk002_pass():
    m = _findings("test_clean.cfg")
    assert m["CHK-002"].status == FindingStatus.PASS, "CHK-002 should PASS (non-default community)"


@pytest.mark.inv("INV-05")
def test_junos_clean_chk004_pass():
    m = _findings("test_clean.cfg")
    assert m["CHK-004"].status == FindingStatus.PASS, "CHK-004 should PASS (syslog configured)"


@pytest.mark.inv("INV-05")
def test_junos_clean_chk005_pass():
    m = _findings("test_clean.cfg")
    assert m["CHK-005"].status == FindingStatus.PASS, "CHK-005 should PASS (NTP configured)"


@pytest.mark.inv("INV-05")
def test_junos_clean_chk006_pass():
    m = _findings("test_clean.cfg")
    assert m["CHK-006"].status == FindingStatus.PASS, "CHK-006 should PASS (no HTTP management)"


# ─── INV-08: findings carry trust class ──────────────────────────────────────

@pytest.mark.inv("INV-08")
def test_junos_findings_carry_trust():
    m = _findings("test_findings.cfg")
    for finding in m.values():
        assert finding.trust, f"Finding {finding.check_id} missing trust class"


# ─── INV-13: determinism ─────────────────────────────────────────────────────

@pytest.mark.inv("INV-13")
def test_junos_parse_deterministic():
    """Parsing the same bytes twice produces identical baselines."""
    raw = (FIXTURES / "test_findings.cfg").read_bytes()
    sha = sha256_bytes(raw)
    parser = JunosParser()
    lines1, _ = parser.parse(raw, sha)
    lines2, _ = parser.parse(raw, sha)
    assert [l.tokens for l in lines1] == [l.tokens for l in lines2]
