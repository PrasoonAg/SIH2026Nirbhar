"""
parsing.service — ParsingService implementation (Phase 2: all 4 vendors).

Uses hand-written grammars in domain/. No third-party parsing libraries.
"""
from __future__ import annotations

from pramana.baseline.api import NormalizedBaseline, UnrecognizedLine
from pramana.parsing.api import ParseError, ParseResult, ParsingService, VendorId
from pramana.parsing.domain.cisco_ios import CiscoIOSParser
from pramana.parsing.domain.fortios import FortiosParser
from pramana.parsing.domain.junos import JunosParser
from pramana.parsing.domain.panos import PanosParser
from pramana.shared_kernel.api import sha256_bytes


# ─── Vendor fingerprints (ordered most-specific first) ───────────────────────

_CISCO_SIGNATURES = [
    b"version ",
    b"hostname ",
    b"service timestamps",
    b"ip ssh version",
    b"interface GigabitEthernet",
    b"interface FastEthernet",
    b"interface Serial",
    b"no service pad",
    b"enable secret",
    b"enable password",
    b"snmp-server community",
    b"line vty",
    b"ntp server",
    b"logging host",
]

_JUNOS_SIGNATURES = [
    b"## Last changed:",
    b"set system host-name",
    b"set interfaces",
    b"groups {",
    b"system {",
    b"interfaces {",
    b"routing-options {",
    b"snmp {",
    b"firewall {",
    b"version ",
]

_PANOS_SIGNATURES = [
    b"<config",
    b"<deviceconfig>",
    b"<devices>",
    b"<vsys>",
    b"<rulebase>",
    b"<snmp-setting>",
    b"<ntp-servers>",
    b"<interface-management-profile>",
]

_FORTIOS_SIGNATURES = [
    b"config system global\n",
    b"config system interface\n",
    b"config firewall policy\n",
    b"config system snmp",
    b"config system ntp\n",
    b"config log syslogd",
    b"\n    set ",
    b"\nend\n",
    b"\nnext\n",
]


def _score_vendor(raw_bytes: bytes, signatures: list[bytes]) -> int:
    return sum(1 for sig in signatures if sig in raw_bytes)


class ParsingServiceImpl(ParsingService):
    """Phase 2 implementation: Cisco IOS, JunOS, PAN-OS, FortiOS."""

    def __init__(self) -> None:
        self._cisco_parser = CiscoIOSParser()
        self._junos_parser = JunosParser()
        self._panos_parser = PanosParser()
        self._fortios_parser = FortiosParser()

    def detect_vendor(self, raw_bytes: bytes) -> VendorId:
        # PAN-OS XML has unambiguous markers — check first
        if b"<config" in raw_bytes and b"<devices>" in raw_bytes:
            return VendorId.PALO_ALTO_PANOS

        scores = {
            VendorId.CISCO_IOS: _score_vendor(raw_bytes, _CISCO_SIGNATURES),
            VendorId.JUNIPER_JUNOS: _score_vendor(raw_bytes, _JUNOS_SIGNATURES),
            VendorId.FORTINET_FORTIOS: _score_vendor(raw_bytes, _FORTIOS_SIGNATURES),
        }
        best = max(scores, key=lambda v: scores[v])
        top_scores = sorted(scores.values(), reverse=True)
        second = top_scores[1]

        if scores[best] == 0:
            return VendorId.UNKNOWN
        if scores[best] == second:
            return VendorId.AMBIGUOUS
        return best

    def parse(self, raw_bytes: bytes, artifact_sha256: str) -> ParseResult:
        vendor = self.detect_vendor(raw_bytes)
        if vendor == VendorId.AMBIGUOUS:
            raise ParseError(
                "Vendor is ambiguous — admin confirmation required before parsing."
            )
        if vendor == VendorId.UNKNOWN:
            raise ParseError(
                "Vendor could not be detected. Verify the file is a supported config format."
            )

        lines_raw = raw_bytes.split(b"\n")
        total_lines = len(lines_raw)
        blank_comment = sum(
            1 for ln in lines_raw
            if not ln.strip() or ln.lstrip().startswith(b"!") or ln.lstrip().startswith(b"#")
        )

        if vendor == VendorId.CISCO_IOS:
            cisco_lines, unrecognized = self._cisco_parser.parse(raw_bytes, artifact_sha256)
            baseline = self._cisco_parser.to_normalized_baseline(
                cisco_lines, unrecognized, artifact_sha256
            )
            recognized = len(cisco_lines)

        elif vendor == VendorId.JUNIPER_JUNOS:
            junos_lines, unrecognized = self._junos_parser.parse(raw_bytes, artifact_sha256)
            baseline = self._junos_parser.to_normalized_baseline(
                junos_lines, unrecognized, artifact_sha256
            )
            recognized = len(junos_lines)

        elif vendor == VendorId.PALO_ALTO_PANOS:
            panos_elems, unrecognized = self._panos_parser.parse(raw_bytes, artifact_sha256)
            baseline = self._panos_parser.to_normalized_baseline(
                panos_elems, unrecognized, artifact_sha256
            )
            recognized = len(panos_elems)

        elif vendor == VendorId.FORTINET_FORTIOS:
            fortios_lines, unrecognized = self._fortios_parser.parse(raw_bytes, artifact_sha256)
            baseline = self._fortios_parser.to_normalized_baseline(
                fortios_lines, unrecognized, artifact_sha256
            )
            recognized = len(fortios_lines)

        else:
            raise ParseError(f"No parser for vendor {vendor.value}")

        return ParseResult(
            vendor_id=vendor,
            baseline=baseline,
            total_lines=total_lines,
            blank_comment_lines=blank_comment,
            unrecognized=tuple(unrecognized),
        )
