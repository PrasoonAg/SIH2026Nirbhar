"""
proposer — public API surface.

Layer:  L2
Track:  1
Tier:   1  (Ollama fallback T2)

INV-02: proposer NEVER imports trustgate and vice versa.
        Their only shared language is baseline.api.

Exports:
  MiniLM anchor index, top-3 + cosine, Ollama fallback seam.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pramana.shared_kernel.api import ModelCard, PramanaError


@dataclass(frozen=True)
class Candidate:
    """One proposal from the proposer."""
    setting_id: str
    anchor_phrase: str
    cosine: float


@dataclass(frozen=True)
class Proposal:
    """Top-3 candidates returned by the proposer for one unrecognized line."""
    candidates: tuple[Candidate, ...]   # up to 3
    model_card: ModelCard
    used_ollama_fallback: bool = False


class ProposerError(PramanaError):
    """Proposer model or index failure."""


class ProposerService:
    """
    Embed an unrecognized line and return top-3 anchor matches.
    STUB — full implementation in Phase 3.
    """

    def propose(self, line_bytes: bytes) -> Proposal:  # noqa: ARG002
        raise NotImplementedError("Phase 3")

    def propose_batch(
        self, lines: list[bytes]
    ) -> list[tuple[bytes, Proposal]]:  # noqa: ARG002
        """Propose for up to 200 unrecognized signatures per audit."""
        raise NotImplementedError("Phase 3")


from pramana.proposer.service import DEFAULT_MODEL_CARD, MiniLMProposerService

__all__ = [
    "ModelCard",
    "Candidate",
    "Proposal",
    "ProposerError",
    "ProposerService",
    "DEFAULT_MODEL_CARD",
    "MiniLMProposerService",
]

