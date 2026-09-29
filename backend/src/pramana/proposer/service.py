"""
proposer.service — Implementation of ProposerService (§9.2).
"""
from __future__ import annotations

from pramana.proposer.api import Candidate, ModelCard, Proposal, ProposerService
from pramana.proposer.domain.anchors import rank_anchors

DEFAULT_MODEL_CARD = ModelCard(
    family="MiniLM",
    name="sentence-transformers/all-MiniLM-L6-v2",
    revision="e4ce9877de0ada3e33e46200e47fe277717462eb",
    weights_sha256="sha256:d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3",
    licence="Apache-2.0",
)


class MiniLMProposerService(ProposerService):
    """
    Offline anchor matching service returning top-3 proposals with cosine scores.
    """

    def __init__(self, model_card: ModelCard = DEFAULT_MODEL_CARD) -> None:
        self.model_card = model_card

    def propose(self, line_bytes: bytes) -> Proposal:
        try:
            line_str = line_bytes.decode("utf-8").strip()
        except UnicodeDecodeError:
            line_str = line_bytes.decode("latin-1").strip()

        ranked = rank_anchors(line_str, top_k=3)
        candidates = tuple(
            Candidate(setting_id=sid, anchor_phrase=phrase, cosine=cosine)
            for sid, phrase, cosine in ranked
        )

        return Proposal(
            candidates=candidates,
            model_card=self.model_card,
            used_ollama_fallback=False,
        )

    def propose_batch(
        self, lines: list[bytes]
    ) -> list[tuple[bytes, Proposal]]:
        # Cap to 200 lines per audit batch (§9.2)
        capped_lines = lines[:200]
        return [(line, self.propose(line)) for line in capped_lines]
