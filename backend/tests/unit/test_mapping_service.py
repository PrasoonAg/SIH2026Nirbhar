"""
unit/test_mapping_service.py — Test MappingService orchestrator, confirm/correct, and ledger chaining.
"""
from __future__ import annotations

from uuid import uuid4
import pytest

from pramana.ledger.adapters.in_memory import InMemoryLedgerAdapter
from pramana.mapping.adapters.in_memory import InMemoryMappingRepository
from pramana.mapping.api import MappingError, MappingState
from pramana.mapping.service import MappingService
from pramana.proposer.api import Candidate, ModelCard, Proposal


@pytest.fixture
def service():
    repo = InMemoryMappingRepository()
    ledger = InMemoryLedgerAdapter()
    return MappingService(repo=repo, ledger=ledger)


def test_full_lifecycle_unmapped_to_provisional_and_corroborated(service):
    admin_alice = uuid4()
    reviewer_bob = uuid4()

    proposal = Proposal(
        candidates=(
            Candidate(setting_id="stp.portfast.default", anchor_phrase="PortFast globally", cosine=0.92),
            Candidate(setting_id="stp.bpduguard.default", anchor_phrase="BPDU guard", cosine=0.68),
        ),
        model_card=ModelCard("MiniLM", "all-MiniLM-L6-v2", "rev1", "hash1", "Apache-2.0"),
    )

    # 1. Propose
    mapping = service.create_proposal(
        vendor_id="cisco_ios",
        dialect_fingerprint="fp_stp_001",
        proposal=proposal,
        actor_id=admin_alice,
    )
    assert mapping.state == MappingState.PROPOSED
    assert len(service.ledger.entries_for(mapping.mapping_id)) == 1

    # 2. Confirm
    raw_line = b"spanning-tree portfast default"
    mapping = service.confirm(
        mapping_id=mapping.mapping_id,
        actor_id=admin_alice,
        target_setting_id="stp.portfast.default",
        raw_line=raw_line,
    )
    assert mapping.state == MappingState.ADMIN_REVIEWED
    assert len(service.ledger.entries_for(mapping.mapping_id)) == 2

    # 3. Gate Passes -> Provisional
    mapping = service.record_gate_outcome(
        mapping_id=mapping.mapping_id,
        actor_id=admin_alice,
        passed=True,
        profile_commit="abc1234",
    )
    assert mapping.state == MappingState.PROVISIONAL
    assert len(service.ledger.entries_for(mapping.mapping_id)) == 3
    assert service.ledger.verify_chain(mapping.mapping_id) is True

    # 4. Blind Second Reviewer -> Corroborated
    mapping, evidence = service.record_second_review(
        mapping_id=mapping.mapping_id,
        reviewer_id=reviewer_bob,
        approved=True,
    )
    assert evidence.weight == 1
    assert mapping.state == MappingState.CORROBORATED
    assert len(service.ledger.entries_for(mapping.mapping_id)) == 4
    assert service.ledger.verify_chain(mapping.mapping_id) is True


def test_gate_failure_transitions_to_rejected_and_absorbs(service):
    admin_alice = uuid4()
    proposal = Proposal(
        candidates=(
            Candidate(setting_id="mgmt.telnet.enabled", anchor_phrase="Telnet access", cosine=0.88),
        ),
        model_card=ModelCard("MiniLM", "all-MiniLM-L6-v2", "rev1", "hash1", "Apache-2.0"),
    )

    mapping = service.create_proposal("cisco_ios", "fp_telnet", proposal, admin_alice)
    mapping = service.confirm(mapping.mapping_id, admin_alice, "mgmt.telnet.enabled", b"transport input telnet")

    # Gate fails
    mapping = service.record_gate_outcome(
        mapping.mapping_id,
        admin_alice,
        passed=False,
        failed_checks=["RegenCheck"],
    )
    assert mapping.state == MappingState.REJECTED
    assert service.ledger.verify_chain(mapping.mapping_id) is True

    # Any attempt to re-confirm or transition raises MappingError (INV-01)
    with pytest.raises(MappingError, match="INV-01"):
        service.confirm(mapping.mapping_id, admin_alice, "mgmt.telnet.enabled", b"transport input telnet")


def test_confirm_unknown_taxonomy_fails(service):
    admin_alice = uuid4()
    proposal = Proposal(
        candidates=(Candidate(setting_id="mgmt.telnet.enabled", anchor_phrase="Telnet", cosine=0.85),),
        model_card=ModelCard("MiniLM", "all-MiniLM-L6-v2", "rev1", "hash1", "Apache-2.0"),
    )

    mapping = service.create_proposal("cisco_ios", "fp_invalid", proposal, admin_alice)

    with pytest.raises(MappingError, match="not found in canonical taxonomy"):
        service.confirm(mapping.mapping_id, admin_alice, "hallucinated.unknown.setting", b"invalid cmd")
