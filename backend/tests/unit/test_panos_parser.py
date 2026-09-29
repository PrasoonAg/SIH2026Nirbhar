"""
unit/test_panos_parser.py — golden tests for the PAN-OS XML parser.
"""
from __future__ import annotations

import pytest
from pathlib import Path

from pramana.compliance.domain.engine import ComplianceServiceImpl
from pramana.compliance.domain.seed_checks import SEED_CHECKS_PHASE2
from pramana.compliance.api import FindingStatus
from pramana.parsing.domain.panos import PanosParser
from pramana.shared_kernel.api import sha256_bytes

FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "configs" / "panos"
COMPLIANCE = ComplianceServiceImpl(SEED_CHECKS_PHASE2)


def _parse(filename: str):
    raw = (FIXTURES / filename).read_bytes()
    parser = PanosParser()
    elems, unrecognized = parser.parse(raw, sha256_bytes(raw))
    return parser.to_normalized_baseline(elems, unrecognized, sha256_bytes(raw))


def _findings(filename: str):
    baseline = _parse(filename)
    return {f.check_id: f for f in COMPLIANCE.evaluate(baseline, f"panos-{filename}", "HEAD")}


# ─── Basic ────────────────────────────────────────────────────────────────────

def test_panos_parser_produces_observations():
    baseline = _parse("test_findings.xml")
    assert len(baseline.observations) > 0


def test_panos_vendor_id():
    baseline = _parse("test_findings.xml")
    assert baseline.vendor_id == "palo_alto_panos"


# ─── Findings fixture ─────────────────────────────────────────────────────────

@pytest.mark.inv("INV-05")
def test_panos_findings_chk001_fail():
    """CHK-001: telnet=yes in mgmt profile → FAIL."""
    m = _findings("test_findings.xml")
    assert m["CHK-001"].status == FindingStatus.FAIL, "CHK-001 should FAIL (telnet in profile)"


@pytest.mark.inv("INV-05")
def test_panos_findings_chk002_fail():
    """CHK-002: SNMP community string = 'public' → FAIL."""
    m = _findings("test_findings.xml")
    assert m["CHK-002"].status == FindingStatus.FAIL, "CHK-002 should FAIL (SNMP public)"


@pytest.mark.inv("INV-05")
def test_panos_findings_chk004_fail():
    """CHK-004: no syslog → FAIL."""
    m = _findings("test_findings.xml")
    assert m["CHK-004"].status == FindingStatus.FAIL, "CHK-004 should FAIL (no syslog)"


@pytest.mark.inv("INV-05")
def test_panos_findings_chk005_fail():
    """CHK-005: no NTP → FAIL."""
    m = _findings("test_findings.xml")
    assert m["CHK-005"].status == FindingStatus.FAIL, "CHK-005 should FAIL (no NTP)"


@pytest.mark.inv("INV-05")
def test_panos_findings_chk006_fail():
    """CHK-006: http=yes in mgmt profile → FAIL."""
    m = _findings("test_findings.xml")
    assert m["CHK-006"].status == FindingStatus.FAIL, "CHK-006 should FAIL (HTTP in profile)"


# ─── Clean fixture ────────────────────────────────────────────────────────────

@pytest.mark.inv("INV-05")
def test_panos_clean_chk001_pass():
    m = _findings("test_clean.xml")
    assert m["CHK-001"].status == FindingStatus.PASS, "CHK-001 should PASS (no telnet)"


@pytest.mark.inv("INV-05")
def test_panos_clean_chk002_pass():
    m = _findings("test_clean.xml")
    assert m["CHK-002"].status == FindingStatus.PASS, "CHK-002 should PASS (non-default SNMP)"


@pytest.mark.inv("INV-05")
def test_panos_clean_chk004_pass():
    m = _findings("test_clean.xml")
    assert m["CHK-004"].status == FindingStatus.PASS, "CHK-004 should PASS (syslog configured)"


@pytest.mark.inv("INV-05")
def test_panos_clean_chk005_pass():
    m = _findings("test_clean.xml")
    assert m["CHK-005"].status == FindingStatus.PASS, "CHK-005 should PASS (NTP configured)"


@pytest.mark.inv("INV-05")
def test_panos_clean_chk006_pass():
    m = _findings("test_clean.xml")
    assert m["CHK-006"].status == FindingStatus.PASS, "CHK-006 should PASS (no HTTP)"


@pytest.mark.inv("INV-08")
def test_panos_findings_carry_trust():
    for f in COMPLIANCE.evaluate(_parse("test_findings.xml"), "panos-x", "HEAD"):
        assert f.trust


@pytest.mark.inv("INV-13")
def test_panos_parse_deterministic():
    raw = (FIXTURES / "test_findings.xml").read_bytes()
    sha = sha256_bytes(raw)
    parser = PanosParser()
    e1, _ = parser.parse(raw, sha)
    e2, _ = parser.parse(raw, sha)
    assert [el.xpath for el in e1] == [el.xpath for el in e2]
