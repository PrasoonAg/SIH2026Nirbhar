"""
shared_kernel.api — PRAMANA shared kernel public surface.

All modules import from here. Nothing else from shared_kernel is public.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ─── Severity ─────────────────────────────────────────────────────────────────

class Severity(str, Enum):
    """Check severity levels with associated weights (§8 / INV-07)."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def weight(self) -> int:
        return {"critical": 20, "high": 10, "medium": 5, "low": 2}[self.value]


# ─── Trust classes ────────────────────────────────────────────────────────────

class TrustClass(str, Enum):
    """Trust classification for findings (INV-05 / INV-08)."""
    PROVISIONAL = "provisional"
    CORROBORATED = "corroborated"
    DETERMINISTIC = "deterministic"


# ─── Hashing ──────────────────────────────────────────────────────────────────

def sha256_bytes(data: bytes) -> str:
    """Return the lowercase hex SHA-256 digest of *data*."""
    return hashlib.sha256(data).hexdigest()


def sha256_str(text: str) -> str:
    """Return the lowercase hex SHA-256 digest of *text* (UTF-8 encoded)."""
    return sha256_bytes(text.encode("utf-8"))


def canonical_json(obj: Any) -> bytes:
    """Return a stable, sorted-key JSON encoding of *obj* as UTF-8 bytes."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


# ─── ID generation ────────────────────────────────────────────────────────────

def new_id() -> str:
    """Return a new random UUIDv4 string."""
    return str(uuid.uuid4())


# ─── Error hierarchy ──────────────────────────────────────────────────────────

class PramanaError(Exception):
    """Base exception for all PRAMANA domain errors."""


class ValidationError(PramanaError):
    """Input data failed validation."""


class NotFoundError(PramanaError):
    """Requested entity does not exist."""


class InvariantViolation(PramanaError):
    """A domain invariant was violated (programming error, not user error)."""


# ─── Domain events ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events."""
    event_id: str = field(default_factory=new_id)


class EventBusPort:
    """Protocol for the in-process event bus."""

    def publish(self, event: DomainEvent) -> None:  # pragma: no cover
        raise NotImplementedError


class NullEventBus(EventBusPort):
    """No-op event bus for testing and stub contexts."""

    def publish(self, event: DomainEvent) -> None:
        pass


# ─── Model Card (INV-02 / INV-17) ───────────────────────────────────────────

@dataclass(frozen=True)
class ModelCard:
    """Descriptor for a bundled model weight file (INV-17 / INV-02)."""
    family: str        # e.g. "MiniLM", "T5", "DeBERTa" — must differ between proposer and verifier
    name: str
    revision: str
    weights_sha256: str
    licence: str

