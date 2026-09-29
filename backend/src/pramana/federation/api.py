"""
federation — public API surface.

Layer:  L5
Track:  5
Tier:   3  (T3 — seams only until Phase 10)

Exports:
  Signed profile-pack export/import.
  A pack is evidence, not authority — imported mappings enter as Proposed.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from pramana.shared_kernel.api import PramanaError


class FederationError(PramanaError):
    """Pack signature, hash or schema verification failure."""


@dataclass(frozen=True)
class PackManifest:
    schema_version: str
    site_id: str
    exported_at: str
    file_hashes: dict[str, str]  # filename → SHA-256


class FederationService:
    """
    T3 — Federated signed profile pack export/import.
    STUB — full implementation in Phase 10.
    """

    def export_pack(self, mapping_ids: list[UUID], out_path: Path) -> Path:  # noqa: ARG002
        raise NotImplementedError("Phase 10 (T3)")

    def import_pack(self, pack_path: Path, actor_id: UUID) -> list[UUID]:  # noqa: ARG002
        """Returns list of new mapping IDs created as Proposed."""
        raise NotImplementedError("Phase 10 (T3)")


__all__ = ["FederationError", "PackManifest", "FederationService"]
