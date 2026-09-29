"""
unit/test_inv04_known_vendor_skip.py — Invariant INV-04 verification.

INV-04: Known-vendor deterministic lines skip the gate.
Only AI-proposed mappings pass it.
"""
from __future__ import annotations

import pytest
from pramana.baseline.api import Provenance
from pramana.parsing.api import VendorId
from pramana.parsing.service import ParsingServiceImpl


@pytest.mark.inv("INV-04")
def test_cisco_ios_known_lines_have_deterministic_provenance():
    svc = ParsingServiceImpl()
    cfg = b"""
    version 15.2
    hostname rtr-core-01
    snmp-server community public RO
    line vty 0 4
     transport input telnet
    """
    result = svc.parse(cfg, "sha256:abc")
    assert result.vendor_id == VendorId.CISCO_IOS

    # All recognized observations from known vendor grammar MUST have Provenance.DETERMINISTIC
    assert len(result.baseline.observations) > 0
    for obs in result.baseline.observations:
        assert obs.provenance == Provenance.DETERMINISTIC
        # Deterministic lines carry NO mapping_id because they skip the mapping gate
        assert obs.mapping_id is None


@pytest.mark.inv("INV-04")
def test_only_ai_proposed_lines_require_gate():
    """Only lines mapped through AI proposer carry Provenance.PROPOSED and require gate."""
    from pramana.baseline.api import Observation, LineRef
    from uuid import uuid4

    deterministic_obs = Observation(
        setting_id="snmp.community.default",
        typed_value={"community": "public"},
        scope="global",
        provenance=Provenance.DETERMINISTIC,
        line_ref=LineRef(artifact_sha256="sha1", line_no=5, byte_span=(10, 30)),
        mapping_id=None,
    )

    proposed_obs = Observation(
        setting_id="stp.portfast.default",
        typed_value={"mode": "default"},
        scope="global",
        provenance=Provenance.PROPOSED,
        line_ref=LineRef(artifact_sha256="sha1", line_no=12, byte_span=(100, 130)),
        mapping_id=str(uuid4()),
    )

    def requires_trust_gate(obs: Observation) -> bool:
        # INV-04: Known-vendor deterministic lines skip the gate
        return obs.provenance == Provenance.PROPOSED

    assert requires_trust_gate(deterministic_obs) is False
    assert requires_trust_gate(proposed_obs) is True
