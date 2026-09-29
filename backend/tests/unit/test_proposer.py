"""
unit/test_proposer.py — Test proposer returns top-3 candidates with cosine scores (§9.2).
"""
from __future__ import annotations

import pytest
from pramana.proposer.api import MiniLMProposerService, Proposal


def test_proposer_unseen_stp_line_returns_top3_with_cosine():
    service = MiniLMProposerService()
    line = b"spanning-tree portfast default"

    proposal: Proposal = service.propose(line)
    assert len(proposal.candidates) == 3
    assert proposal.model_card.family == "MiniLM"

    # Top candidate should be stp.portfast.default with high cosine
    top1 = proposal.candidates[0]
    assert top1.setting_id == "stp.portfast.default"
    assert top1.cosine > 0.70
    assert "PortFast" in top1.anchor_phrase or "portfast" in top1.anchor_phrase

    # Candidates should be sorted by cosine descending
    for i in range(len(proposal.candidates) - 1):
        assert proposal.candidates[i].cosine >= proposal.candidates[i + 1].cosine


def test_proposer_unseen_telnet_line():
    service = MiniLMProposerService()
    line = b"transport input telnet"

    proposal = service.propose(line)
    assert len(proposal.candidates) >= 1
    top1 = proposal.candidates[0]
    assert top1.setting_id == "mgmt.telnet.enabled"
    assert top1.cosine > 0.60


def test_proposer_batch_caps_at_200():
    service = MiniLMProposerService()
    lines = [f"custom command line {i}".encode() for i in range(250)]

    batch_results = service.propose_batch(lines)
    assert len(batch_results) == 200
    for line, prop in batch_results:
        assert isinstance(prop, Proposal)
        assert len(prop.candidates) <= 3
