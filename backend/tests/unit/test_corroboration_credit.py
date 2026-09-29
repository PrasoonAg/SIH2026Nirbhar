"""
unit/test_corroboration_credit.py — Invariant INV-06 verification.

INV-06: Corroboration needs new independent evidence.
Same actor or same checker = weight 0. Repeats add nothing.
First-pass gate classes cannot corroborate.
"""
from __future__ import annotations

from uuid import uuid4
import pytest

from pramana.mapping.api import EvidenceItem, credit


@pytest.mark.inv("INV-06")
def test_first_pass_classes_never_corroborate():
    mapping_id = uuid4()
    for cls_name in ["ADMIN_REVIEW", "GATE_REGEN", "GATE_LEXICAL", "GATE_SECOND_MODEL"]:
        item = EvidenceItem(
            evidence_id=uuid4(),
            mapping_id=mapping_id,
            cls=cls_name,
            actor_id=uuid4(),
            checker_id=None,
            input_fingerprint="fp1",
            payload_ref="ref1",
            weight=1,
            reason="passed gate",
        )
        weight, reason = credit(item, [])
        assert weight == 0
        assert "cannot corroborate" in reason


@pytest.mark.inv("INV-06")
def test_second_reviewer_same_actor_gets_weight_zero():
    mapping_id = uuid4()
    actor_alice = uuid4()

    # Alice was the initial admin reviewer
    history = [
        EvidenceItem(
            evidence_id=uuid4(),
            mapping_id=mapping_id,
            cls="ADMIN_REVIEW",
            actor_id=actor_alice,
            checker_id=None,
            input_fingerprint="fp1",
            payload_ref="ref1",
            weight=1,
            reason="Alice confirmed",
        )
    ]

    # Alice tries to be the second reviewer
    alice_second_review = EvidenceItem(
        evidence_id=uuid4(),
        mapping_id=mapping_id,
        cls="SECOND_REVIEWER",
        actor_id=actor_alice,
        checker_id=None,
        input_fingerprint="fp1",
        payload_ref="ref2",
        weight=1,
        reason="Alice blind review",
    )

    weight, reason = credit(alice_second_review, history)
    assert weight == 0
    assert "independent" in reason.lower()


@pytest.mark.inv("INV-06")
def test_second_reviewer_independent_actor_gets_weight_one():
    mapping_id = uuid4()
    actor_alice = uuid4()
    actor_bob = uuid4()

    history = [
        EvidenceItem(
            evidence_id=uuid4(),
            mapping_id=mapping_id,
            cls="ADMIN_REVIEW",
            actor_id=actor_alice,
            checker_id=None,
            input_fingerprint="fp1",
            payload_ref="ref1",
            weight=1,
            reason="Alice confirmed",
        )
    ]

    bob_review = EvidenceItem(
        evidence_id=uuid4(),
        mapping_id=mapping_id,
        cls="SECOND_REVIEWER",
        actor_id=actor_bob,
        checker_id=None,
        input_fingerprint="fp1",
        payload_ref="ref2",
        weight=1,
        reason="Bob approved",
    )

    weight, reason = credit(bob_review, history)
    assert weight == 1
    assert "Credited" in reason


@pytest.mark.inv("INV-06")
def test_duplicate_evidence_class_repeat_adds_nothing():
    mapping_id = uuid4()
    actor_bob = uuid4()
    actor_charlie = uuid4()

    credited_bob = EvidenceItem(
        evidence_id=uuid4(),
        mapping_id=mapping_id,
        cls="SECOND_REVIEWER",
        actor_id=actor_bob,
        checker_id=None,
        input_fingerprint="fp1",
        payload_ref="ref1",
        weight=1,
        reason="Bob approved",
    )

    history = [credited_bob]

    # Charlie also reviews, but SECOND_REVIEWER is already credited
    charlie_review = EvidenceItem(
        evidence_id=uuid4(),
        mapping_id=mapping_id,
        cls="SECOND_REVIEWER",
        actor_id=actor_charlie,
        checker_id=None,
        input_fingerprint="fp1",
        payload_ref="ref2",
        weight=1,
        reason="Charlie approved",
    )

    weight, reason = credit(charlie_review, history)
    assert weight == 0
    assert "already credited" in reason
