"""
identity — public API surface.

Layer:  L1
Track:  5
Tier:   1

Exports:
  Local users, roles (operator, admin, reviewer, auditor), sessions, Actor.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from pramana.shared_kernel.api import PramanaError


class Role(str, Enum):
    OPERATOR = "operator"
    ADMIN = "admin"
    REVIEWER = "reviewer"
    AUDITOR = "auditor"


@dataclass(frozen=True)
class Actor:
    """An authenticated principal performing an action."""
    actor_id: UUID
    username: str
    role: Role


class AuthError(PramanaError):
    """Authentication or authorisation failure."""


class IdentityService(object):
    """Stub — full implementation in Phase 1."""

    def authenticate(self, username: str, password: str) -> Actor:  # noqa: ARG002
        raise NotImplementedError

    def get_actor(self, actor_id: UUID) -> Actor:  # noqa: ARG002
        raise NotImplementedError


__all__ = ["Role", "Actor", "AuthError", "IdentityService"]
