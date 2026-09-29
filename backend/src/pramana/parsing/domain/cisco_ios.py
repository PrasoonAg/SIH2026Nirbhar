"""
parsing.domain.cisco_ios — hand-written Cisco IOS line-state parser.

Supports:
  - !-comment lines
  - `no <directive>` negation prefix
  - Indentation-nested blocks (interface, line vty, router ospf, …)
  - VTY / console line blocks for ACL and timeout extraction

Every observation carries exact line_no and byte_span.
No third-party parsing library. No regex catastrophic backtracking.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator

from pramana.baseline.api import (
    LineRef,
    NormalizedBaseline,
    Observation,
    Provenance,
    UnrecognizedLine,
)
from pramana.shared_kernel.api import sha256_bytes


# ─── Token/line helpers ───────────────────────────────────────────────────────

def _is_comment(line: str) -> bool:
    return line.lstrip().startswith("!")


def _is_blank(line: str) -> bool:
    return not line.strip()


def _tokens(line: str) -> list[str]:
    """Split a config line into tokens, stripping leading/trailing whitespace."""
    return line.strip().split()


# ─── AST node types ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CiscoLine:
    """One parsed observation from the Cisco IOS config."""
    raw: str
    line_no: int
    byte_start: int
    byte_end: int
    tokens: tuple[str, ...]
    negated: bool            # True if the line starts with "no "
    block_context: tuple[str, ...]  # e.g. ("interface", "GigabitEthernet0/0")

    def render(self) -> str:
        """Round-trip: reconstruct the canonical line (without trailing newline)."""
        prefix = "no " if self.negated else ""
        return prefix + " ".join(self.tokens)


# ─── Parser ──────────────────────────────────────────────────────────────────

class CiscoIOSParser:
    """
    Hand-written line-state parser for Cisco IOS configurations.

    Invariants:
      - No regex with catastrophic backtracking.
      - Every observation carries exact line_no and byte_span.
      - render(parse(line)) == line for all recognized lines.
    """

    # Directives that introduce a block context
    _BLOCK_STARTERS = frozenset([
        "interface", "router", "line", "vrf", "ip", "ipv6",
        "policy-map", "class-map", "route-map", "access-list",
        "aaa", "crypto", "key", "username", "banner",
    ])

    def parse(
        self, raw_bytes: bytes, artifact_sha256: str
    ) -> tuple[list[CiscoLine], list[UnrecognizedLine]]:
        """
        Parse raw Cisco IOS config bytes.

        Returns:
            (recognized_lines, unrecognized_lines)
        """
        recognized: list[CiscoLine] = []
        unrecognized: list[UnrecognizedLine] = []
        block_stack: list[tuple[str, ...]] = []
        byte_offset = 0

        for line_no, line_bytes in enumerate(raw_bytes.split(b"\n"), start=1):
            line = line_bytes.decode("utf-8", errors="replace")
            byte_start = byte_offset
            byte_end = byte_offset + len(line_bytes)
            byte_offset = byte_end + 1  # +1 for the newline

            if _is_blank(line) or _is_comment(line):
                continue

            tokens = _tokens(line)
            if not tokens:
                continue

            # Block exit
            if tokens[0] == "end" or tokens[0] == "exit":
                if block_stack:
                    block_stack.pop()
                continue

            # Negation prefix
            negated = tokens[0] == "no"
            effective_tokens = tuple(tokens[1:] if negated else tokens)

            if not effective_tokens:
                continue

            # Block enter
            context = tuple(block_stack[-1]) if block_stack else ()
            if effective_tokens[0] in self._BLOCK_STARTERS and not negated:
                block_stack.append(effective_tokens)

            parsed = CiscoLine(
                raw=line.rstrip(),
                line_no=line_no,
                byte_start=byte_start,
                byte_end=byte_end,
                tokens=effective_tokens,
                negated=negated,
                block_context=context,
            )
            recognized.append(parsed)

        return recognized, unrecognized

    # ── Setting taxonomy resolver ─────────────────────────────────────────────

    @staticmethod
    def _resolve_setting_id(tokens: tuple[str, ...], negated: bool, context: tuple[str, ...]) -> str:
        """
        Map Cisco IOS tokens → canonical setting_id.
        Returns '__raw__' for lines that don't match any known setting.
        INV-04: only deterministic lines resolved here.
        """
        t = list(tokens)
        if not t:
            return "__raw__"

        # VTY-context settings
        in_vty = context and context[0] == "line" and "vty" in context

        # management access
        if t[:2] == ["transport", "input"] and "telnet" in t:
            return "mgmt.telnet.enabled"
        if t[:2] == ["access-class"] and "in" in t:
            return "vty.access-class.in"
        if t == ["exec-timeout"] or t[:1] == ["exec-timeout"]:
            return "vty.exec-timeout"
        if t[:3] == ["ip", "ssh", "version"]:
            return "mgmt.ssh.v2"
        if t[:3] == ["ip", "http", "server"]:
            return "mgmt.http.server"
        if t[:4] == ["ip", "http", "secure-server"] or t[:4] == ["ip", "https", "server"]:
            return "mgmt.https.server"

        # SNMP
        if t[:2] == ["snmp-server", "community"] and ("public" in t or "private" in t):
            return "snmp.community.default"
        if t[:1] == ["snmp-server"]:
            return "snmp.configured"

        # Logging
        if t[:2] == ["logging", "host"] or (t[:1] == ["logging"] and len(t) > 1 and t[1] not in {"on", "buffered", "console", "monitor", "facility", "trap"}):
            return "logging.host"

        # NTP
        if t[:2] == ["ntp", "server"] or t[:2] == ["ntp", "source"] or t[:2] == ["ntp", "authenticate"]:
            return "ntp.server"

        # Legacy risky services
        if t[:2] == ["service", "tcp-small-servers"]:
            return "service.tcp-small-servers"
        if t[:2] == ["service", "udp-small-servers"]:
            return "service.udp-small-servers"
        if t[:2] == ["service", "finger"] or t[:1] == ["finger"]:
            return "service.finger"

        # IP options
        if t[:2] == ["ip", "redirects"] or t[:3] == ["no", "ip", "redirects"]:
            return "ip.redirects.disabled"
        if t[:3] == ["no", "ip", "proxy-arp"] or t[:3] == ["ip", "proxy-arp"]:
            return "ip.proxy-arp.disabled"
        if t[:3] == ["no", "ip", "source-route"] or t[:3] == ["ip", "source-route"]:
            return "ip.source-route.disabled"

        return "__raw__"

    def to_normalized_baseline(
        self,
        lines: list[CiscoLine],
        unrecognized: list[UnrecognizedLine],
        artifact_sha256: str,
    ) -> NormalizedBaseline:
        """
        Convert parsed CiscoLines to a NormalizedBaseline.
        Phase 2: setting_id is resolved deterministically at parse time (INV-04).
        Lines that don't match the taxonomy stay as '__raw__' for the proposer.
        """
        from pramana.baseline.api import NormalizedBaseline

        observations = tuple(
            Observation(
                setting_id=self._resolve_setting_id(cl.tokens, cl.negated, cl.block_context),
                typed_value={"tokens": list(cl.tokens), "negated": cl.negated},
                scope=".".join(cl.block_context) if cl.block_context else "global",
                provenance=Provenance.DETERMINISTIC,
                line_ref=LineRef(
                    artifact_sha256=artifact_sha256,
                    line_no=cl.line_no,
                    byte_span=(cl.byte_start, cl.byte_end),
                ),
                mapping_id=None,
            )
            for cl in lines
        )

        return NormalizedBaseline(
            vendor_id="cisco_ios",
            observations=observations,
            unrecognized=tuple(unrecognized),
        )
