# proposer

## Purpose
Embeds unrecognized config lines against a precomputed MiniLM anchor index
and returns the top-3 candidate settings with cosine scores.

## Public API (`api.py`)
| Export | Description |
|---|---|
| `ModelCard` | Model descriptor (family, name, revision, weights_sha256, licence) |
| `Candidate` | One ranked proposal (setting_id, anchor_phrase, cosine) |
| `Proposal` | Top-3 candidates + model card |
| `ProposerService` | `propose(line_bytes)` / `propose_batch(lines)` |

## Invariants
- **INV-02** `proposer` NEVER imports `trustgate` and vice versa.
- **INV-11** `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`; loads local paths only.
- **INV-17** Model weights SHA-256 verified at startup.
- Model family must differ from the verifier (checked at startup + each gate run).
- Ollama fallback is T2 only; T1 is embedding top-3 only.

## Track / Tier
Track 1 · Tier 1 (Ollama fallback T2)

## Owner
Track 1
