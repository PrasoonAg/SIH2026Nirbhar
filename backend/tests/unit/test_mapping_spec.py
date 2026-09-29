"""
unit/test_mapping_spec.py — Test MappingSpec match and render round-trip and induce_spec.
"""
from __future__ import annotations

from pramana.baseline.api import MappingSpec, SlotType, Token, match, render
from pramana.mapping.api import induce_spec


def test_mapping_spec_roundtrip_explicit():
    # Pattern: "spanning-tree portfast <WORD>"
    spec = MappingSpec(
        vendor_id="cisco_ios",
        dialect_fingerprint="abc",
        pattern=(
            Token(literal="spanning-tree"),
            Token(literal="portfast"),
            Token(is_slot=True, slot_name="mode", slot_type=SlotType.WORD),
        ),
        target_setting_id="stp.portfast.default",
        render_template="spanning-tree portfast {mode}",
    )

    line = b"spanning-tree portfast default"
    frag = match(spec, line)
    assert frag is not None
    assert frag["mode"] == "default"

    rendered = render(spec, frag)
    assert rendered == line


def test_induce_spec_and_roundtrip():
    line = b"snmp-server community public RO"
    spec = induce_spec(line, "snmp.community.default", "cisco_ios")

    assert spec.vendor_id == "cisco_ios"
    assert spec.target_setting_id == "snmp.community.default"
    assert len(spec.pattern) == 4

    frag = match(spec, line)
    assert frag is not None
    rendered = render(spec, frag)
    assert rendered == line


def test_induce_spec_numeric_slots():
    line = b"exec-timeout 15 0"
    spec = induce_spec(line, "vty.exec-timeout", "cisco_ios")

    frag = match(spec, line)
    assert frag is not None
    assert frag["slot_1"] == 15
    assert frag["slot_2"] == 0

    rendered = render(spec, frag)
    assert rendered == line
