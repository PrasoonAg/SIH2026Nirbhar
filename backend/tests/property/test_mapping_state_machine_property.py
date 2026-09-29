"""
property/test_mapping_state_machine_property.py — Property tests for state machine and INV-01.

Hypothesis property tests:
  - Random valid event sequences never reach an illegal state.
  - Rejected state is strictly absorbing under any random event sequence (INV-01).
"""
from __future__ import annotations

from uuid import uuid4
import pytest
from hypothesis import given, settings, strategies as st

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

# Strategy producing any arbitrary domain event
domain_events = st.one_of(
    st.builds(AnchorMatchedEvent, candidates_count=st.integers(min_value=1, max_value=5), top1_cosine=st.floats(0.0, 1.0), proposer_family=st.just("MiniLM")),
    st.builds(AdminConfirmedEvent, actor_id=st.uuids(), target_setting_id=st.just("stp.portfast.default")),
    st.builds(AdminCorrectedEvent, actor_id=st.uuids(), target_setting_id=st.just("mgmt.ssh.v2")),
    st.builds(GateFiredEvent, gate_run_id=st.uuids(), verifier_family=st.just("DeBERTa")),
    st.builds(GatePassedEvent, gate_run_id=st.uuids(), profile_commit=st.just("abc1234")),
    st.builds(GateFailedEvent, gate_run_id=st.uuids(), failed_checks=st.just(["RegenCheck"])),
    st.builds(GateErroredEvent, gate_run_id=st.uuids(), error_message=st.just("timeout")),
    st.builds(DecaySampledEvent, cycle_id=st.just("c1")),
    st.builds(EvidenceRecordedEvent, evidence_id=st.uuids()),
    st.builds(CorroboratedEvent, evidence_ids=st.just([uuid4()]), profile_commit=st.just("def5678")),
    st.builds(ReGatePassedEvent, gate_run_id=st.uuids()),
    st.builds(ReGateFailedEvent, gate_run_id=st.uuids()),
    st.builds(ReGateErroredEvent, gate_run_id=st.uuids()),
)


@pytest.mark.inv("INV-01")
@given(events=st.lists(domain_events, min_size=1, max_size=20))
@settings(max_examples=50)
def test_hypothesis_rejected_is_absorbing(events):
    """Once Rejected, no event sequence can transition out of REJECTED."""
    mapping = Mapping(
        mapping_id=uuid4(),
        vendor_id="cisco_ios",
        state=MappingState.REJECTED,
        dialect_fingerprint="fp1",
    )

    for ev in events:
        with pytest.raises(MappingError):
            mapping.transition(ev)
        assert mapping.state == MappingState.REJECTED


@given(events=st.lists(domain_events, min_size=1, max_size=30))
@settings(max_examples=50)
def test_hypothesis_state_machine_never_reaches_corrupted_state(events):
    """Applying any random sequence of events either transitions legally or raises MappingError."""
    mapping = Mapping(
        mapping_id=uuid4(),
        vendor_id="cisco_ios",
        state=MappingState.UNMAPPED,
        dialect_fingerprint="fp1",
    )

    for ev in events:
        try:
            mapping.transition(ev)
        except MappingError:
            pass  # Expected on illegal transition

        # State must always be a valid member of MappingState
        assert isinstance(mapping.state, MappingState)
        assert mapping.state in MappingState
