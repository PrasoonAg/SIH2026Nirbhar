# crypto

## Purpose
Ed25519 signing and verification for PDF reports and federated packs.
**T3 — seams only until Phase 10.**

## Public API (`api.py`)
| Export | Description |
|---|---|
| `CryptoError` | Key / signing failure |
| `KeyPair` | Ed25519 key pair (key_id = SHA-256 of public key) |
| `CryptoService` | generate_keys, sign_bytes, verify_signature |

## Invariants
- Private key file must be mode `0600` under `data/keys/`.
- INV-17: missing or invalid model / key integrity → fail closed.

## Track / Tier
Track 5 · Tier 3

## Owner
Track 5
