"""
tests/conftest.py
=================
Shared fixtures: loads data/manifest.json and parametrises models by tier/class.
Manifest schema (actual):
  name, file, class_, rows, cols, nnz, integers, reference_objective,
  sense, ref_source, split, tier, sha256, highs_time_s, origin

Tier naming in manifest: T1-tiny, T2-small, T3-stretch, S1-degenerate, S2-illconditioned-*
"""

from __future__ import annotations
import json
import pytest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent           # backend/
_PROTO = _BACKEND.parent          # Prototype/

# Resolve data/ — prefer sibling data/, fall back to Prototype/data/
_DATA_CANDIDATES = [
    _BACKEND / "data",
    _PROTO / "data",
]

DATA_DIR: Path | None = None
for _c in _DATA_CANDIDATES:
    if (_c / "manifest.json").exists():
        DATA_DIR = _c
        break


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "slow: long-running benchmarks")


@pytest.fixture(scope="session")
def manifest() -> list[dict]:
    if DATA_DIR is None:
        pytest.skip("data/manifest.json not found")
    raw = json.loads((DATA_DIR / "manifest.json").read_text())
    # Actual schema: {"models": [...], ...}
    if isinstance(raw, dict):
        return raw.get("models", [])
    return raw  # fallback: list


@pytest.fixture(scope="session")
def netlib_t1(manifest: list[dict]) -> list[dict]:
    """T1-tiny LP models (pure LP, no integers)."""
    return [m for m in manifest
            if m.get("tier", "").startswith("T1") and m.get("class_") == "LP"]


@pytest.fixture(scope="session")
def netlib_t2(manifest: list[dict]) -> list[dict]:
    """T2-small LP models."""
    return [m for m in manifest
            if m.get("tier", "").startswith("T2") and m.get("class_") == "LP"]


@pytest.fixture(scope="session")
def milp_t1(manifest: list[dict]) -> list[dict]:
    """T1-tiny MILP/MIP models."""
    return [m for m in manifest
            if m.get("tier", "").startswith("T1")
            and m.get("class_") in ("MILP", "MIP")]


@pytest.fixture(scope="session")
def stress_s1(manifest: list[dict]) -> list[dict]:
    """S1 degenerate/cycling stress models."""
    return [m for m in manifest if m.get("tier", "").startswith("S1")]


@pytest.fixture(scope="session")
def stress_s2(manifest: list[dict]) -> list[dict]:
    """S2 ill-conditioned stress models."""
    return [m for m in manifest if m.get("tier", "").startswith("S2")]


@pytest.fixture(scope="session")
def infeas_models(manifest: list[dict]) -> list[dict]:
    """Infeasible/unbounded status models."""
    return [m for m in manifest
            if m.get("class_") in ("INFEASIBLE", "UNBOUNDED", "STATUS")]


def model_path(entry: dict) -> Path:
    """Resolve the absolute path for a manifest entry (uses 'file' key)."""
    rel = entry.get("file", "")
    if DATA_DIR is None:
        raise FileNotFoundError("DATA_DIR not set")
    p = DATA_DIR / rel
    if p.exists():
        return p
    raise FileNotFoundError(f"Model file not found: {rel!r} (looked in {DATA_DIR})")
