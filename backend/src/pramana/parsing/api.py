"""
parsing.api — Public surface for the parsing module.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Sequence

from pramana.baseline.api import NormalizedBaseline, UnrecognizedLine


# ─── Vendor IDs ───────────────────────────────────────────────────────────────

class VendorId(str, Enum):
    """Detected vendor identifier."""
    CISCO_IOS = "cisco_ios"
    JUNIPER_JUNOS = "juniper_junos"
    PALO_ALTO_PANOS = "palo_alto_panos"
    FORTINET_FORTIOS = "fortinet_fortios"
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"


# ─── Parse result ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ParseResult:
    """Result of parsing a raw config artifact."""
    vendor_id: VendorId
    baseline: NormalizedBaseline
    total_lines: int
    blank_comment_lines: int
    unrecognized: tuple[UnrecognizedLine, ...]

    @property
    def recognized_lines(self) -> int:
        return self.total_lines - self.blank_comment_lines - len(self.unrecognized)


# ─── Errors ───────────────────────────────────────────────────────────────────

class ParseError(Exception):
    """Config file could not be parsed (ambiguous vendor, corrupt data, etc.)."""


# ─── Port protocol ────────────────────────────────────────────────────────────

class ParsingService(Protocol):
    """Port — implemented by ParsingServiceImpl in service.py (injected by bootstrap)."""

    def detect_vendor(self, raw_bytes: bytes) -> VendorId:
        ...

    def parse(self, raw_bytes: bytes, artifact_sha256: str) -> ParseResult:
        ...
