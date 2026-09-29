"""
parsing.domain.panos — hand-written PAN-OS XML config parser.

PAN-OS configurations are XML. We use Python's stdlib xml.etree.ElementTree
(no network access; purely structural parsing).

Every observation carries exact line_no and byte_span approximation
(XML doesn't store line numbers; we record the element path and byte position).
No third-party library.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass

from pramana.baseline.api import (
    LineRef,
    NormalizedBaseline,
    Observation,
    Provenance,
    UnrecognizedLine,
)
from pramana.parsing.api import ParseError


# ─── AST node types ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PanosElement:
    """One configuration element extracted from PAN-OS XML."""
    xpath: str                        # XPath-like path, e.g. "devices/entry/deviceconfig/system"
    tag: str
    attrib: dict[str, str]
    text: str | None
    line_no_approx: int               # approximate line number (byte-based)
    byte_start: int
    byte_end: int


# ─── Parser ──────────────────────────────────────────────────────────────────

class PanosParser:
    """
    Hand-written XML-structural parser for Palo Alto PAN-OS configurations.

    Extracts semantically meaningful elements (SNMP, NTP, management profiles)
    and maps them to canonical setting_id values.
    """

    def parse(
        self, raw_bytes: bytes, artifact_sha256: str
    ) -> tuple[list[PanosElement], list[UnrecognizedLine]]:
        unrecognized: list[UnrecognizedLine] = []
        elements: list[PanosElement] = []

        try:
            root = ET.fromstring(raw_bytes)
        except ET.ParseError as exc:
            raise ParseError(f"PAN-OS XML parse error: {exc}") from exc

        # Walk the tree and extract meaningful elements
        self._walk(root, "", raw_bytes, elements)
        return elements, unrecognized

    def _walk(
        self,
        elem: ET.Element,
        parent_path: str,
        raw_bytes: bytes,
        out: list[PanosElement],
    ) -> None:
        name = elem.get("name", "")
        path = f"{parent_path}/{elem.tag}" + (f"[@name='{name}']" if name else "")

        # Approximate byte position by finding the tag in raw bytes
        tag_bytes = f"<{elem.tag}".encode()
        byte_start = raw_bytes.find(tag_bytes)
        if byte_start < 0:
            byte_start = 0
        byte_end = byte_start + len(tag_bytes)
        line_no_approx = raw_bytes[:byte_start].count(b"\n") + 1

        out.append(PanosElement(
            xpath=path,
            tag=elem.tag,
            attrib=dict(elem.attrib),
            text=(elem.text or "").strip() or None,
            line_no_approx=line_no_approx,
            byte_start=byte_start,
            byte_end=byte_end,
        ))

        for child in elem:
            self._walk(child, path, raw_bytes, out)

    # ── Setting taxonomy resolver ──────────────────────────────────────────────

    @staticmethod
    def _resolve_setting_id(elem: PanosElement) -> str:
        """Map PAN-OS XPath + text → canonical setting_id."""
        xpath = elem.xpath.lower()
        text = (elem.text or "").lower().strip()
        tag = elem.tag.lower()

        # SNMP community strings
        if "snmp" in xpath and tag == "snmp-community-string":
            if text in ("public", "private"):
                return "snmp.community.default"
            if text:
                return "snmp.configured"

        # NTP
        if "ntp-server-address" in tag:
            return "ntp.server"
        if "ntp" in xpath and tag in ("ntp-server-address", "primary-ntp-server", "secondary-ntp-server"):
            return "ntp.server"

        # Syslog
        if "syslog" in xpath and tag == "server":
            return "logging.host"
        if "log-export" in xpath and tag in ("server",):
            return "logging.host"

        # Management profile HTTP / telnet
        if "interface-management-profile" in xpath:
            if tag == "http" and text in ("yes", "true", "1"):
                return "mgmt.http.server"
            if tag == "https" and text in ("yes", "true", "1"):
                return "mgmt.https.server"
            if tag == "telnet" and text in ("yes", "true", "1"):
                return "mgmt.telnet.enabled"

        # Permitted-ip = management ACL
        if tag == "permitted-ip" or "permitted-ip" in xpath:
            return "vty.access-class.in"
        if tag == "ip-netmask" and "permitted-ip" in xpath:
            return "vty.access-class.in"

        # SSH (PAN-OS always SSHv2, but check for explicit config)
        if "ssh" in xpath and tag in ("ssh", "protocol-version"):
            return "mgmt.ssh.v2"

        return "__raw__"

    def to_normalized_baseline(
        self,
        elements: list[PanosElement],
        unrecognized: list[UnrecognizedLine],
        artifact_sha256: str,
    ) -> NormalizedBaseline:
        """Convert PanosElements to a NormalizedBaseline."""
        observations = []
        for el in elements:
            sid = self._resolve_setting_id(el)
            if sid == "__raw__":
                continue  # Only include known-setting observations (INV-04)
            observations.append(Observation(
                setting_id=sid,
                typed_value={"xpath": el.xpath, "text": el.text, "tag": el.tag},
                scope=el.xpath,
                provenance=Provenance.DETERMINISTIC,
                line_ref=LineRef(
                    artifact_sha256=artifact_sha256,
                    line_no=el.line_no_approx,
                    byte_span=(el.byte_start, el.byte_end),
                ),
                mapping_id=None,
            ))

        return NormalizedBaseline(
            vendor_id="palo_alto_panos",
            observations=tuple(observations),
            unrecognized=tuple(unrecognized),
        )
