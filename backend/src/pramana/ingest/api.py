"""
ingest.api — Public surface for the ingest module.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol


# ─── Errors ───────────────────────────────────────────────────────────────────

class IngestError(Exception):
    """General ingestion failure."""


class ZipGuardError(IngestError):
    """ZIP file failed a safety guard (bomb, traversal, nested archive, etc.)."""


# ─── Domain types ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Artifact:
    """
    A content-addressed config file artifact.

    Original bytes are stored verbatim and never modified (INV-16).
    SHA-256 of the content is the primary key.
    """
    artifact_id: str        # UUID
    sha256: str             # hex digest — the content address
    filename: str
    size_bytes: int
    vendor_hint: str | None  # optional user-supplied vendor hint


@dataclass(frozen=True)
class Device:
    """A network device registered in the system."""
    device_id: str
    hostname: str
    site_id: str | None
    vendor_hint: str | None


@dataclass(frozen=True)
class Site:
    """An organizational site grouping devices."""
    site_id: str
    name: str
    description: str | None


# ─── Port protocol ────────────────────────────────────────────────────────────

class IngestService(Protocol):
    """Port — implemented in ingest/service.py (injected by bootstrap)."""

    def ingest_bytes(
        self,
        raw_bytes: bytes,
        filename: str,
        device_id: str | None = None,
        vendor_hint: str | None = None,
    ) -> Artifact:
        """Store raw bytes content-addressed; deduplicate by SHA-256."""
        ...

    def ingest_zip(
        self,
        zip_bytes: bytes,
        filename: str,
    ) -> list[Artifact]:
        """Unpack a ZIP (with guards), store each member as an artifact."""
        ...

    def get_artifact(self, artifact_id: str) -> Artifact:
        ...

    def read_artifact_bytes(self, artifact_id: str) -> bytes:
        """Return the original bytes of an artifact (immutable, INV-16)."""
        ...
