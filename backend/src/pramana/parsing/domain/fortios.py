"""
parsing.domain.fortios — hand-written FortiOS configuration parser.

FortiOS uses a flat block-and-set syntax:
    config <section>
        edit <id>
            set <key> <value>...
        next
    end

Every observation carries exact line_no and byte_span.
No third-party library.
"""
from __future__ import annotations

from dataclasses import dataclass

from pramana.baseline.api import (
    LineRef,
    NormalizedBaseline,
    Observation,
    Provenance,
    UnrecognizedLine,
)


# ─── AST node ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FortiosLine:
    """One parsed statement from a FortiOS config."""
    raw: str
    line_no: int
    byte_start: int
    byte_end: int
    tokens: tuple[str, ...]          # tokens of the statement
    block_context: tuple[str, ...]   # e.g. ("config system global",)
    edit_context: str | None         # current edit ID if inside edit...next
    verb: str                        # "set", "config", "edit", "next", "end", etc.


# ─── Parser ──────────────────────────────────────────────────────────────────

class FortiosParser:
    """
    Hand-written parser for FortiGate (FortiOS) configuration format.

    Grammar highlights:
    - `config <section>` opens a block (pushed to config_stack)
    - `edit <id>` opens an entry within a config block
    - `set <key> <value>` is a leaf statement
    - `next` closes an edit block
    - `end` closes the current config block
    """

    def parse(
        self, raw_bytes: bytes, artifact_sha256: str
    ) -> tuple[list[FortiosLine], list[UnrecognizedLine]]:
        recognized: list[FortiosLine] = []
        unrecognized: list[UnrecognizedLine] = []

        # Stack of config-block context strings
        config_stack: list[str] = []
        edit_context: str | None = None
        byte_offset = 0

        for line_no, line_bytes in enumerate(raw_bytes.split(b"\n"), start=1):
            line = line_bytes.decode("utf-8", errors="replace")
            byte_start = byte_offset
            byte_end = byte_offset + len(line_bytes)
            byte_offset = byte_end + 1

            stripped = line.strip()

            # Skip blank lines
            if not stripped:
                continue

            tokens = tuple(stripped.split())
            if not tokens:
                continue

            verb = tokens[0].lower()

            if verb == "config":
                # Open a new config block
                section = " ".join(tokens[1:])
                config_stack.append(section)
                edit_context = None
                context = tuple(config_stack)
            elif verb == "end":
                edit_context = None
                if config_stack:
                    config_stack.pop()
                context = tuple(config_stack)
                continue  # Don't produce an observation for structural keywords
            elif verb == "edit":
                edit_context = " ".join(tokens[1:])
                context = tuple(config_stack)
                continue
            elif verb == "next":
                edit_context = None
                context = tuple(config_stack)
                continue
            else:
                context = tuple(config_stack)

            fl = FortiosLine(
                raw=line.rstrip(),
                line_no=line_no,
                byte_start=byte_start,
                byte_end=byte_end,
                tokens=tokens,
                block_context=context,
                edit_context=edit_context,
                verb=verb,
            )
            recognized.append(fl)

        return recognized, unrecognized

    # ── Setting taxonomy resolver ──────────────────────────────────────────────

    @staticmethod
    def _resolve_setting_id(fl: FortiosLine) -> str:
        """Map FortiOS block context + tokens → canonical setting_id."""
        t = list(fl.tokens)
        ctx = list(fl.block_context)
        edit = fl.edit_context or ""

        if fl.verb != "set":
            return "__raw__"

        # Derive key and values (tokens[0]=set, tokens[1]=key, tokens[2:]=values)
        if len(t) < 2:
            return "__raw__"
        key = t[1].lower()
        values = [v.lower() for v in t[2:]]

        # system global settings
        if "system global" in ctx or ctx == ["system global"]:
            if key == "admin-telnet":
                if "enable" in values:
                    return "mgmt.telnet.enabled"
                return "__raw__"
            if key == "admin-ssh-v1":
                return "mgmt.ssh.v2"  # Presence means SSH v1 setting exists

        # System interface — allowaccess (handled via multi-observation in to_normalized_baseline)
        if any("system interface" in c for c in ctx):
            if key == "allowaccess":
                # Returns a synthetic key so to_normalized_baseline can fan out
                return "__allowaccess__"
            if key == "trusted-hosts":
                return "vty.access-class.in"

        # SNMP community name
        if any("system snmp community" in c for c in ctx):
            if key == "name":
                name_val = values[0] if values else ""
                if name_val in ("public", "private"):
                    return "snmp.community.default"
                if name_val:
                    return "snmp.configured"

        # Admin trusted-hosts
        if any("system admin" in c for c in ctx):
            if key == "trusted-hosts":
                return "vty.access-class.in"

        # NTP
        if any("system ntp" in c for c in ctx):
            if key == "server" or "ntpserver" in ctx:
                return "ntp.server"
        if any("ntpserver" in c for c in ctx):
            if key == "server":
                return "ntp.server"

        # Syslog
        if any("log syslogd" in c for c in ctx):
            if key == "server":
                return "logging.host"
            if key == "status" and "enable" in values:
                return "logging.host"

        return "__raw__"

    def to_normalized_baseline(
        self,
        lines: list[FortiosLine],
        unrecognized: list[UnrecognizedLine],
        artifact_sha256: str,
    ) -> NormalizedBaseline:
        """Convert FortiosLines to a NormalizedBaseline.
        
        `allowaccess` lines fan out into multiple observations (one per protocol).
        """
        observations = []

        for fl in lines:
            sid = self._resolve_setting_id(fl)

            if sid == "__allowaccess__":
                # Fan out: one observation per protocol in allowaccess
                t = list(fl.tokens)
                values = [v.lower() for v in t[2:]]
                protocol_map = {
                    "telnet": "mgmt.telnet.enabled",
                    "http": "mgmt.http.server",
                    "https": "mgmt.https.server",
                    "ssh": "mgmt.ssh.v2",
                }
                for proto, proto_sid in protocol_map.items():
                    if proto in values:
                        observations.append(Observation(
                            setting_id=proto_sid,
                            typed_value={
                                "tokens": list(fl.tokens),
                                "context": list(fl.block_context),
                                "edit": fl.edit_context,
                                "proto": proto,
                            },
                            scope=" > ".join(fl.block_context) if fl.block_context else "global",
                            provenance=Provenance.DETERMINISTIC,
                            line_ref=LineRef(
                                artifact_sha256=artifact_sha256,
                                line_no=fl.line_no,
                                byte_span=(fl.byte_start, fl.byte_end),
                            ),
                            mapping_id=None,
                        ))
                continue

            if sid == "__raw__":
                continue

            observations.append(Observation(
                setting_id=sid,
                typed_value={
                    "tokens": list(fl.tokens),
                    "context": list(fl.block_context),
                    "edit": fl.edit_context,
                },
                scope=" > ".join(fl.block_context) if fl.block_context else "global",
                provenance=Provenance.DETERMINISTIC,
                line_ref=LineRef(
                    artifact_sha256=artifact_sha256,
                    line_no=fl.line_no,
                    byte_span=(fl.byte_start, fl.byte_end),
                ),
                mapping_id=None,
            ))

        return NormalizedBaseline(
            vendor_id="fortinet_fortios",
            observations=tuple(observations),
            unrecognized=tuple(unrecognized),
        )
