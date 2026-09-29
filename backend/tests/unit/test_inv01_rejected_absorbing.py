"""
unit/test_inv01_rejected_absorbing.py — Invariant INV-01 verification.

INV-01: No override from Rejected. Rejected is strictly absorbing.
No event or transition can move a mapping out of Rejected.
Only a NEW mapping can be proposed linking the old one via supersedes.
"""
from __future__ import annotations

from uuid import uuid4
import pytest

from pramana.mapping.api import Mapping, MappingError, MappingState
from pramana.mapping.domain.state_machine import (
    AnchorMatchedEvent,
    AdminConfirmedEvent,
    AdminCorrectedEvent,
    GateFiredEvent,
    GatePassedEvent,
    GateFailedEvent,
    GateErroredEvent,
    DecaySampledEvent,
    EvidenceRecordedEvent,
    CorroboratedEvent,
    ReGatePassedEvent,
    ReGateFailedEvent,
    ReGateErroredEvent,
)


@pytest.mark.inv("INV-01")
def test_rejected_is_absorbing_for_all_events():
    """Verify every known domain event fails when applied to a REJECTED mapping."""
    mapping = Mapping(
        mapping_id=uuid4(),
        vendor_id="cisco_ios",
        state=MappingState.REJECTED,
        dialect_fingerprint="abc",
    )

    all_events = [
        AnchorMatchedEvent(candidates_count=2, top1_cosine=0.9, proposer_family="MiniLM"),
        AdminConfirmedEvent(actor_id=uuid4(), target_setting_id="stp.portfast.default"),
        AdminCorrectedEvent(actor_id=uuid4(), target_setting_id="stp.portfast.default"),
        GateFiredEvent(gate_run_id=uuid4(), verifier_family="DeBERTa"),
        GatePassedEvent(gate_run_id=uuid4(), profile_commit="commit1"),
        GateFailedEvent(gate_run_id=uuid4(), failed_checks=["RegenCheck"]),
        GateErroredEvent(gate_run_id=uuid4(), error_message="timeout"),
        DecaySampledEvent(cycle_id="cycle-1"),
        EvidenceRecordedEvent(evidence_id=uuid4()),
        CorroboratedEvent(evidence_ids=[uuid4()], profile_commit="commit2"),
        ReGatePassedEvent(gate_run_id=uuid4()),
        ReGateFailedEvent(gate_run_id=uuid4()),
        ReGateErroredEvent(gate_run_id=uuid4()),
    ]

    for ev in all_events:
        with pytest.raises(MappingError, match="INV-01: Rejected is absorbing"):
            mapping.transition(ev)

        # State must remain REJECTED
        assert mapping.state == MappingState.REJECTED


@pytest.mark.inv("INV-01")
def test_re_proposal_creates_new_mapping_with_supersedes():
    """An admin may only create a NEW proposal linked by supersedes."""
    rejected_id = uuid4()
    rejected_mapping = Mapping(
        mapping_id=rejected_id,
        vendor_id="cisco_ios",
        state=MappingState.REJECTED,
        dialect_fingerprint="fp1",
    )

    # Re-propose from scratch
    new_mapping_id = uuid4()
    new_proposal = Mapping(
        mapping_id=new_mapping_id,
        vendor_id="cisco_ios",
        state=MappingState.PROPOSED,
        dialect_fingerprint="fp1",
        supersedes=rejected_id,
    )

    assert new_proposal.mapping_id != rejected_mapping.mapping_id
    assert new_proposal.supersedes == rejected_id
    assert rejected_mapping.state == MappingState.REJECTED
    assert new_proposal.state == MappingState.PROPOSED
