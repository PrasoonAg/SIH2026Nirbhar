"""
unit/test_cisco_ios_parser.py — Cisco IOS parser tests (Phase 1).

Tests:
  - Vendor detection
  - Parser produces expected observations
  - Golden fixture findings (line numbers)
  - Round-trip: render(parse(line)) == line
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pramana.compliance.domain.engine import ComplianceServiceImpl
from pramana.compliance.domain.seed_checks import SEED_CHECKS_PHASE1
from pramana.compliance.api import FindingStatus
from pramana.parsing.service import ParsingServiceImpl
from pramana.parsing.api import VendorId
from pramana.parsing.domain.cisco_ios import CiscoIOSParser
from pramana.shared_kernel.api import sha256_bytes

FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "configs" / "cisco_ios"


# ─── Vendor detection ─────────────────────────────────────────────────────────

def test_detect_cisco_ios() -> None:
    raw = (FIXTURES / "test_findings.cfg").read_bytes()
    svc = ParsingServiceImpl()
    assert svc.detect_vendor(raw) == VendorId.CISCO_IOS


def test_detect_not_junos() -> None:
    raw = b"set system host-name myrouter\nset interfaces ge-0/0/0 unit 0 family inet\n"
    svc = ParsingServiceImpl()
    vendor = svc.detect_vendor(raw)
    assert vendor != VendorId.CISCO_IOS


# ─── Parser produces observations ─────────────────────────────────────────────

def test_parser_returns_observations() -> None:
    raw = (FIXTURES / "test_findings.cfg").read_bytes()
    parser = CiscoIOSParser()
    artifact_sha256 = sha256_bytes(raw)
    lines, unrecognized = parser.parse(raw, artifact_sha256)
    # Should produce many recognized lines
    assert len(lines) > 5


def test_parser_skips_comments_and_blanks() -> None:
    cfg = b"! This is a comment\n\nhostname myrouter\n"
    parser = CiscoIOSParser()
    lines, _ = parser.parse(cfg, "dummy_sha")
    assert len(lines) == 1
    assert lines[0].tokens == ("hostname", "myrouter")


def test_parser_detects_negation() -> None:
    cfg = b"no ip http server\n"
    parser = CiscoIOSParser()
    lines, _ = parser.parse(cfg, "dummy_sha")
    assert len(lines) == 1
    assert lines[0].negated is True
    assert lines[0].tokens == ("ip", "http", "server")


def test_parser_line_numbers() -> None:
    """Line numbers must be 1-indexed and reflect actual file line positions."""
    cfg = b"! comment\nhostname router\n"
    parser = CiscoIOSParser()
    lines, _ = parser.parse(cfg, "dummy_sha")
    # "hostname router" is line 2
    assert lines[0].line_no == 2


# ─── Round-trip: render(parse(line)) == line ─────────────────────────────────

@pytest.mark.inv("INV-13")
@pytest.mark.parametrize("raw_line", [
    b"hostname myrouter",
    b"no ip http server",
    b"snmp-server community public RO",
    b"transport input telnet ssh",
    b"access-class MGMT-ACCESS in",
    b"exec-timeout 5 0",
    b"ip ssh version 2",
    b"logging host 10.0.0.100",
])
def test_cisco_round_trip(raw_line: bytes) -> None:
    """render(parse(line)) must equal the original line (INV-13 determinism)."""
    parser = CiscoIOSParser()
    lines, _ = parser.parse(raw_line + b"\n", "dummy_sha")
    assert len(lines) == 1
    rendered = lines[0].render().encode("utf-8")
    assert rendered == raw_line, f"Round-trip failed: {rendered!r} != {raw_line!r}"


# ─── Golden fixture findings ──────────────────────────────────────────────────

@pytest.mark.inv("INV-05")
def test_findings_fixture_all_fail() -> None:
    """
    Golden fixture test_findings.cfg must produce:
      CHK-001 FAIL (Telnet enabled)
      CHK-002 FAIL (Default SNMP community)
      CHK-003 FAIL (No VTY ACL)
    """
    raw = (FIXTURES / "test_findings.cfg").read_bytes()
    artifact_sha256 = sha256_bytes(raw)
    svc = ParsingServiceImpl()
    result = svc.parse(raw, artifact_sha256)

    compliance = ComplianceServiceImpl(SEED_CHECKS_PHASE1)
    findings = compliance.evaluate(result.baseline, "dev-fixture-01", "HEAD")

    finding_map = {f.check_id: f for f in findings}

    assert finding_map["CHK-001"].status == FindingStatus.FAIL, "CHK-001 should FAIL (telnet present)"
    assert finding_map["CHK-002"].status == FindingStatus.FAIL, "CHK-002 should FAIL (public community)"
    assert finding_map["CHK-003"].status == FindingStatus.FAIL, "CHK-003 should FAIL (no VTY ACL)"


@pytest.mark.inv("INV-05")
def test_clean_fixture_all_pass() -> None:
    """
    Golden fixture test_clean.cfg must produce:
      CHK-001 PASS (SSH only, no telnet)
      CHK-002 PASS (non-default community)
      CHK-003 PASS (VTY ACL present)
    """
    raw = (FIXTURES / "test_clean.cfg").read_bytes()
    artifact_sha256 = sha256_bytes(raw)
    svc = ParsingServiceImpl()
    result = svc.parse(raw, artifact_sha256)

    compliance = ComplianceServiceImpl(SEED_CHECKS_PHASE1)
    findings = compliance.evaluate(result.baseline, "dev-clean-01", "HEAD")

    finding_map = {f.check_id: f for f in findings}

    assert finding_map["CHK-001"].status == FindingStatus.PASS, "CHK-001 should PASS (no telnet)"
    assert finding_map["CHK-002"].status == FindingStatus.PASS, "CHK-002 should PASS (non-default community)"
    assert finding_map["CHK-003"].status == FindingStatus.PASS, "CHK-003 should PASS (ACL present)"


@pytest.mark.inv("INV-05")
def test_all_findings_carry_trust_class() -> None:
    """INV-08: every finding must carry a trust class."""
    raw = (FIXTURES / "test_findings.cfg").read_bytes()
    artifact_sha256 = sha256_bytes(raw)
    svc = ParsingServiceImpl()
    result = svc.parse(raw, artifact_sha256)
    compliance = ComplianceServiceImpl(SEED_CHECKS_PHASE1)
    findings = compliance.evaluate(result.baseline, "dev1", "HEAD")

    for finding in findings:
        assert finding.trust, f"Finding {finding.check_id} missing trust class (INV-08)"
