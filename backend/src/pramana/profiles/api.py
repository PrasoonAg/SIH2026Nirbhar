"""
profiles — public API surface.

Layer:  L2
Track:  2
Tier:   1

Exports:
  Git-backed versioned vendor profiles, diff, rollback.
  A mapping is usable in an audit ONLY if it appears in HEAD AND its DB state
  is Provisional or Corroborated.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pramana.shared_kernel.api import PramanaError


@dataclass(frozen=True)
class ProfileCommit:
    commit_hash: str
    author: str
    message: str


class ProfileError(PramanaError):
    """Git profile store failure."""


class ProfileStorePort:
    """
    Protocol for the Git profile store adapter.
    Library: pygit2 (preferred) or dulwich (fallback) — see ADR-0003.
    STUB — full implementation in Phase 4.
    """

    def commit_mapping(
        self,
        mapping_id: UUID,
        mapping_json: dict[str, object],
        actor: str,
        ledger_seq: int,
    ) -> ProfileCommit:  # noqa: ARG002
        raise NotImplementedError("Phase 4")

    def head_mapping_ids(self) -> frozenset[UUID]:
        """Return mapping IDs that appear in the HEAD tree."""
        raise NotImplementedError("Phase 4")

    def reconcile(self) -> list[str]:
        """Startup check: detect DB/Git divergence. Returns list of alert messages."""
        raise NotImplementedError("Phase 4")

    def rollback(self, target_commit: str, actor: str) -> ProfileCommit:  # noqa: ARG002
        """Create a revert commit. Never rewrites history."""
        raise NotImplementedError("Phase 4")


__all__ = ["ProfileCommit", "ProfileError", "ProfileStorePort"]
