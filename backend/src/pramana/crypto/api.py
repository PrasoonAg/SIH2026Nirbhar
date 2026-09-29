"""
crypto — public API surface.

Layer:  L1
Track:  5
Tier:   3 (T3 — seams only in Phase 0)

Exports:
  Ed25519 key management, sign/verify, file hashing.
  The private-key file is mode 0600 under data/keys/.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pramana.shared_kernel.api import PramanaError


class CryptoError(PramanaError):
    """Signing, verification or key management failure."""


@dataclass
class KeyPair:
    """Ed25519 key pair.  STUB — full implementation in Phase 10."""
    key_id: str      # SHA-256 fingerprint of the public key (hex)
    public_pem: str


class CryptoService:
    """STUB — full implementation in Phase 10."""

    def generate_keys(self, out_dir: Path) -> KeyPair:  # noqa: ARG002
        raise NotImplementedError("Phase 10")

    def sign_bytes(
        self, data: bytes, private_key_path: Path
    ) -> dict[str, str]:  # noqa: ARG002
        raise NotImplementedError("Phase 10")

    def verify_signature(  # noqa: ARG002
        self,
        data: bytes,
        sig_json: dict[str, str],
        public_pem: str,
    ) -> bool:
        raise NotImplementedError("Phase 10")


__all__ = ["CryptoError", "KeyPair", "CryptoService"]
