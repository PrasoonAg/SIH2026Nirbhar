"""
parsing.domain.junos — hand-written JunOS hierarchical config parser.

Supports:
  - JunOS hierarchical (curly-brace) format
  - Comment lines starting with '#' or '//'
  - Block nesting via { ... }
  - Stanza-level setting extraction

Every observation carries exact line_no and byte_span.
No third-party library. No regex catastrophic backtracking.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from pramana.baseline.api import (
    LineRef,
    NormalizedBaseline,
    Observation,
    Provenance,
    UnrecognizedLine,
)
from pramana.shared_kernel.api import sha256_bytes


# ─── AST node types ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class JunosLine:
    """One parsed line from a JunOS hierarchical config."""
    raw: str
    line_no: int
    byte_start: int
    byte_end: int
    tokens: tuple[str, ...]          # tokens after stripping indent/semicolons
    block_context: tuple[str, ...]   # e.g. ("system", "services")
    is_block_open: bool              # True if line ends with '{'


# ─── Parser ──────────────────────────────────────────────────────────────────

class JunosParser:
    """
    Hand-written parser for Juniper JunOS hierarchical configuration format.

    Grammar highlights:
    - Comments: ## ... or /* ... */ or lines starting with #
    - Block opens: <keyword> { (block_context pushed)
    - Block closes: } (block_context popped)
    - Statements: <keyword> <value>; (semicolon terminated)
    - version and system stanzas at the top level
    """

    def parse(
        self, raw_bytes: bytes, artifact_sha256: str
    ) -> tuple[list[JunosLine], list[UnrecognizedLine]]:
        recognized: list[JunosLine] = []
        unrecognized: list[UnrecognizedLine] = []
        block_stack: list[tuple[str, ...]] = []
        byte_offset = 0

        for line_no, line_bytes in enumerate(raw_bytes.split(b"\n"), start=1):
            line = line_bytes.decode("utf-8", errors="replace")
            byte_start = byte_offset
            byte_end = byte_offset + len(line_bytes)
            byte_offset = byte_end + 1

            stripped = line.strip()

            # Skip blank lines and comment lines
            if not stripped:
                continue
            if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("/*"):
                continue

            # Strip trailing semicolon and whitespace
            content = stripped.rstrip(";").strip()

            # Block close
            if content == "}" or stripped == "};":
                if block_stack:
                    block_stack.pop()
                continue

            # Block open — line ends with '{'
            is_block_open = stripped.endswith("{") or stripped.endswith("{ }")
            if is_block_open:
                # Remove the '{' and any trailing content for the context
                context_part = stripped.rstrip(" {").rstrip()
                tokens = tuple(context_part.split())
                current_context = tuple(block_stack[-1]) if block_stack else ()
                block_stack.append((*current_context, *tokens))

                jl = JunosLine(
                    raw=line.rstrip(),
                    line_no=line_no,
                    byte_start=byte_start,
                    byte_end=byte_end,
                    tokens=tokens,
                    block_context=current_context,
                    is_block_open=True,
                )
                recognized.append(jl)
                continue

            # Regular statement
            tokens = tuple(content.split())
            if not tokens:
                continue

            context = tuple(block_stack[-1]) if block_stack else ()
            jl = JunosLine(
                raw=line.rstrip(),
                line_no=line_no,
                byte_start=byte_start,
                byte_end=byte_end,
                tokens=tokens,
                block_context=context,
                is_block_open=False,
            )
            recognized.append(jl)

        return recognized, unrecognized

    # ── Setting taxonomy resolver ──────────────────────────────────────────────

    @staticmethod
    def _resolve_setting_id(tokens: tuple[str, ...], context: tuple[str, ...]) -> str:
        """
        Map JunOS tokens + block context → canonical setting_id.
        INV-04: deterministic lines only.
        """
        ctx = list(context)
        t = list(tokens)

        # system > services > telnet
        if "system" in ctx and "services" in ctx:
            if t and t[0] == "telnet":
                return "mgmt.telnet.enabled"
            if t[:2] == ["ssh", "protocol-version"]:
                return "mgmt.ssh.v2"
            if "web-management" in ctx and "http" in ctx:
                return "mgmt.http.server"
            if "web-management" in ctx and "https" in ctx:
                return "mgmt.https.server"

        # system > syslog > host <ip>
        if "system" in ctx and "syslog" in ctx:
            # "host X.X.X.X" stanza = remote syslog
            if len(ctx) >= 3 and ctx[-2] == "syslog":
                # block_context ends with syslog,host,<ip>
                return "logging.host"
            if t and t[0] == "host":
                return "logging.host"

        # system > ntp > server
        if "system" in ctx and "ntp" in ctx:
            if t and t[0] == "server":
                return "ntp.server"

        # snmp > community <name> — detect public/private
        if "snmp" in ctx and "community" in ctx:
            # The community name is in the parent stanza block context
            # e.g. context = ("snmp", "community", "public")
            community_name = ""
            for i, c in enumerate(ctx):
                if c == "community" and i + 1 < len(ctx):
                    community_name = ctx[i + 1]
                    break
            if community_name.lower() in ("public", "private"):
                return "snmp.community.default"
            # Any other community stanza = snmp.configured
            if community_name:
                return "snmp.configured"

        # management interface firewall filter (ACL)
        if "firewall" in ctx and "filter" in ctx:
            return "vty.access-class.in"

        # Interface filter input reference
        if "interfaces" in ctx and t[:2] == ["filter", "input"]:
            return "vty.access-class.in"
        if "interfaces" in ctx and t[:2] == ["filter", "output"]:
            return "__raw__"

        # SSH protocol version as standalone statement
        if t[:3] == ["set", "system", "services"] and "protocol-version" in t:
            return "mgmt.ssh.v2"

        return "__raw__"

    def to_normalized_baseline(
        self,
        lines: list[JunosLine],
        unrecognized: list[UnrecognizedLine],
        artifact_sha256: str,
    ) -> NormalizedBaseline:
        """Convert JunosLines to a NormalizedBaseline."""
        observations = tuple(
            Observation(
                setting_id=self._resolve_setting_id(jl.tokens, jl.block_context),
                typed_value={"tokens": list(jl.tokens), "context": list(jl.block_context)},
                scope=".".join(jl.block_context) if jl.block_context else "global",
                provenance=Provenance.DETERMINISTIC,
                line_ref=LineRef(
                    artifact_sha256=artifact_sha256,
                    line_no=jl.line_no,
                    byte_span=(jl.byte_start, jl.byte_end),
                ),
                mapping_id=None,
            )
            for jl in lines
        )
        return NormalizedBaseline(
            vendor_id="juniper_junos",
            observations=observations,
            unrecognized=tuple(unrecognized),
        )
