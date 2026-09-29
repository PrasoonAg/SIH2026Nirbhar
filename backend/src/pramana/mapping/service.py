"""
mapping.service — Application service orchestrating the trust lifecycle (§6.2, §6.4).
"""
from __future__ import annotations

from uuid import UUID, uuid4

from pramana.ledger.api import LedgerPort, create_entry
from pramana.mapping.api import (
    EvidenceItem,
    Mapping,
    MappingError,
    MappingRepository,
    MappingState,
    credit,
    induce_spec,
)
from pramana.mapping.domain.state_machine import (
    AdminConfirmedEvent,
    AdminCorrectedEvent,
    AnchorMatchedEvent,
    CorroboratedEvent,
    GateFailedEvent,
    GatePassedEvent,
)
from pramana.parsing.domain.taxonomy import SETTING_IDS
from pramana.proposer.api import Proposal


class MappingService:
    """Use-case orchestrator for mapping aggregate and ledger synchronization."""

    def __init__(self, repo: MappingRepository, ledger: LedgerPort) -> None:
        self.repo = repo
        self.ledger = ledger

    def create_proposal(
        self,
        vendor_id: str,
        dialect_fingerprint: str,
        proposal: Proposal,
        actor_id: UUID,
    ) -> Mapping:
        """Create a new proposed mapping after proposer matched anchors."""
        mapping_id = uuid4()
        mapping = Mapping(
            mapping_id=mapping_id,
            vendor_id=vendor_id,
            state=MappingState.UNMAPPED,
            dialect_fingerprint=dialect_fingerprint,
            proposal=proposal,
        )

        # Transition UNMAPPED -> PROPOSED
        event = AnchorMatchedEvent(
            candidates_count=len(proposal.candidates),
            top1_cosine=proposal.candidates[0].cosine if proposal.candidates else 0.0,
            proposer_family=proposal.model_card.family,
        )
        mapping.transition(event)

        # Ledger transition (INV-12)
        ledger_entry = create_entry(
            sequence=1,
            mapping_id=mapping_id,
            actor_id=actor_id,
            event_kind="AnchorMatched",
            payload={
                "vendor_id": vendor_id,
                "dialect_fingerprint": dialect_fingerprint,
                "top1_candidate": proposal.candidates[0].setting_id if proposal.candidates else "",
                "top1_cosine": proposal.candidates[0].cosine if proposal.candidates else 0.0,
            },
            prev_hash="",
        )
        self.ledger.append(ledger_entry)
        self.repo.save(mapping)
        return mapping

    def confirm(
        self,
        mapping_id: UUID,
        actor_id: UUID,
        target_setting_id: str,
        raw_line: bytes,
    ) -> Mapping:
        """Admin confirms a proposed mapping target (§6.2)."""
        mapping = self.repo.get(mapping_id)

        if target_setting_id not in SETTING_IDS:
            raise MappingError(f"Target setting '{target_setting_id}' not found in canonical taxonomy")

        # Induce spec deterministically
        spec = induce_spec(raw_line, target_setting_id, mapping.vendor_id)
        mapping.spec = spec

        # Transition PROPOSED -> ADMIN_REVIEWED
        event = AdminConfirmedEvent(actor_id=actor_id, target_setting_id=target_setting_id)
        mapping.transition(event)

        # Ledger transition with forward link
        entries = self.ledger.entries_for(mapping_id)
        prev_hash = entries[-1].entry_hash if entries else ""
        next_seq = len(entries) + 1

        ledger_entry = create_entry(
            sequence=next_seq,
            mapping_id=mapping_id,
            actor_id=actor_id,
            event_kind="AdminConfirmed",
            payload={
                "target_setting_id": target_setting_id,
                "spec_fingerprint": spec.dialect_fingerprint,
            },
            prev_hash=prev_hash,
        )
        self.ledger.append(ledger_entry)
        self.repo.save(mapping)
        return mapping

    def correct(
        self,
        mapping_id: UUID,
        actor_id: UUID,
        new_target_setting_id: str,
        raw_line: bytes,
    ) -> Mapping:
        """Admin corrects a proposed mapping with a different target (§6.2)."""
        mapping = self.repo.get(mapping_id)

        if new_target_setting_id not in SETTING_IDS:
            raise MappingError(f"Target setting '{new_target_setting_id}' not in canonical taxonomy")

        spec = induce_spec(raw_line, new_target_setting_id, mapping.vendor_id)
        mapping.spec = spec

        event = AdminCorrectedEvent(actor_id=actor_id, target_setting_id=new_target_setting_id)
        mapping.transition(event)

        entries = self.ledger.entries_for(mapping_id)
        prev_hash = entries[-1].entry_hash if entries else ""
        next_seq = len(entries) + 1

        ledger_entry = create_entry(
            sequence=next_seq,
            mapping_id=mapping_id,
            actor_id=actor_id,
            event_kind="AdminCorrected",
            payload={
                "new_target_setting_id": new_target_setting_id,
                "spec_fingerprint": spec.dialect_fingerprint,
            },
            prev_hash=prev_hash,
        )
        self.ledger.append(ledger_entry)
        self.repo.save(mapping)
        return mapping

    def record_gate_outcome(
        self,
        mapping_id: UUID,
        actor_id: UUID,
        passed: bool,
        profile_commit: str = "abc1234",
        failed_checks: list[str] | None = None,
    ) -> Mapping:
        """Record the outcome of the 3-check trust gate run."""
        mapping = self.repo.get(mapping_id)
        gate_run_id = uuid4()

        # Transient transition to GATING
        from pramana.mapping.domain.state_machine import GateFiredEvent
        mapping.transition(GateFiredEvent(gate_run_id=gate_run_id, verifier_family="DeBERTa"))

        if passed:
            mapping.transition(GatePassedEvent(gate_run_id=gate_run_id, profile_commit=profile_commit))
            event_kind = "GatePassed"
            payload = {"gate_run_id": str(gate_run_id), "profile_commit": profile_commit}
        else:
            checks = failed_checks or ["RegenCheck"]
            mapping.transition(GateFailedEvent(gate_run_id=gate_run_id, failed_checks=checks))
            event_kind = "GateFailed"
            payload = {"gate_run_id": str(gate_run_id), "failed_checks": checks}

        entries = self.ledger.entries_for(mapping_id)
        prev_hash = entries[-1].entry_hash if entries else ""
        next_seq = len(entries) + 1

        ledger_entry = create_entry(
            sequence=next_seq,
            mapping_id=mapping_id,
            actor_id=actor_id,
            event_kind=event_kind,
            payload=payload,
            prev_hash=prev_hash,
        )
        self.ledger.append(ledger_entry)
        self.repo.save(mapping)
        return mapping

    def record_second_review(
        self,
        mapping_id: UUID,
        reviewer_id: UUID,
        approved: bool,
        profile_commit: str = "def5678",
    ) -> tuple[Mapping, EvidenceItem]:
        """Blind second reviewer evaluation and corroboration credit (INV-06)."""
        mapping = self.repo.get(mapping_id)

        evidence = EvidenceItem(
            evidence_id=uuid4(),
            mapping_id=mapping_id,
            cls="SECOND_REVIEWER",
            actor_id=reviewer_id,
            checker_id=None,
            input_fingerprint=mapping.dialect_fingerprint,
            payload_ref=str(mapping_id),
            weight=1 if approved else 0,
            reason="Second reviewer evaluation",
        )

        weight, reason = credit(evidence, mapping.evidence_items)
        credited_evidence = EvidenceItem(
            evidence_id=evidence.evidence_id,
            mapping_id=evidence.mapping_id,
            cls=evidence.cls,
            actor_id=evidence.actor_id,
            checker_id=evidence.checker_id,
            input_fingerprint=evidence.input_fingerprint,
            payload_ref=evidence.payload_ref,
            weight=weight,
            reason=reason,
        )
        mapping.evidence_items.append(credited_evidence)

        # If mapping is in PROVISIONAL and receives credited independent evidence
        if mapping.state == MappingState.PROVISIONAL and weight > 0:
            from pramana.mapping.domain.state_machine import EvidenceRecordedEvent
            mapping.transition(EvidenceRecordedEvent(evidence_id=credited_evidence.evidence_id))
            mapping.transition(CorroboratedEvent(evidence_ids=[credited_evidence.evidence_id], profile_commit=profile_commit))

        entries = self.ledger.entries_for(mapping_id)
        prev_hash = entries[-1].entry_hash if entries else ""
        next_seq = len(entries) + 1

        ledger_entry = create_entry(
            sequence=next_seq,
            mapping_id=mapping_id,
            actor_id=reviewer_id,
            event_kind="SecondReviewRecorded",
            payload={
                "evidence_id": str(credited_evidence.evidence_id),
                "weight": weight,
                "reason": reason,
                "resulting_state": mapping.state.value,
            },
            prev_hash=prev_hash,
        )
        self.ledger.append(ledger_entry)
        self.repo.save(mapping)
        return mapping, credited_evidence
