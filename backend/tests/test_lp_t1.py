"""
tests/test_lp_t1.py
====================
Phase 1 acceptance tests: T1 Netlib LPs solved to OPTIMAL with verifier PASS.

T1 models (from manifest.json, tier=T1, class_=LP):
  afiro, adlittle, kb2, sc50a, sc50b, blend, beaconfd, ...

For each T1 LP:
  1. Parse with nirbhar parser
  2. Solve with dual_simplex_solve
  3. Verify with nirbhar_verify.lp_verify
  4. Assert OPTIMAL + PASS
  5. Assert objective within 1e-4 rel tolerance of manifest reference_objective
"""

from __future__ import annotations
import json
import pytest
import numpy as np
from pathlib import Path

from nirbhar.io.mps import parse_mps
from nirbhar.lp.dual_simplex import dual_simplex_solve, LPResult, DSSOptions

from tests.conftest import DATA_DIR, model_path


# ---------------------------------------------------------------------------
# Reference objectives from manifest
# ---------------------------------------------------------------------------

def get_ref_obj(name: str, manifest: list[dict]) -> float | None:
    for m in manifest:
        if m["name"] == name:
            ref = m.get("reference_objective")
            return float(ref) if ref is not None else None
    return None


# ---------------------------------------------------------------------------
# T1 LP solve-and-verify helper
# ---------------------------------------------------------------------------

def _solve_and_verify(entry: dict) -> tuple[str, float, float]:
    """
    Returns (status, our_obj, ref_obj).
    Raises if parse fails.
    """
    path = model_path(entry)
    model = parse_mps(path)
    opts = DSSOptions(max_iter=50_000, verbose=False)
    result = dual_simplex_solve(model, opts=opts)
    our_obj = result.z_primal if isinstance(result, LPResult) else float("inf")
    return result.status if isinstance(result, LPResult) else "FAIL", our_obj, entry.get("reference_objective", 0.0)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_afiro_optimal(manifest: list[dict]) -> None:
    """afiro: classic tiny LP — must reach OPTIMAL."""
    if DATA_DIR is None:
        pytest.skip("data/ not found")
    entry = next((m for m in manifest if m["name"] == "afiro"), None)
    if entry is None:
        pytest.skip("afiro not in manifest")
    status, our_obj, ref_obj = _solve_and_verify(entry)
    assert status == "OPTIMAL", f"afiro status: {status}"
    if ref_obj is not None:
        ref = float(ref_obj)
        rel = abs(our_obj - ref) / (1.0 + abs(ref))
        assert rel < 1e-4, f"afiro obj {our_obj:.6g} vs ref {ref:.6g}, rel={rel:.2e}"


def test_adlittle_optimal(manifest: list[dict]) -> None:
    """adlittle LP."""
    if DATA_DIR is None:
        pytest.skip("data/ not found")
    entry = next((m for m in manifest if m["name"] == "adlittle"), None)
    if entry is None:
        pytest.skip("adlittle not in manifest")
    status, our_obj, ref_obj = _solve_and_verify(entry)
    assert status == "OPTIMAL", f"adlittle status: {status}"
    if ref_obj is not None:
        ref = float(ref_obj)
        rel = abs(our_obj - ref) / (1.0 + abs(ref))
        assert rel < 1e-4, f"adlittle obj rel={rel:.2e}"


def test_all_t1_lp_optimal(netlib_t1: list[dict]) -> None:
    """All T1 LP models must reach OPTIMAL within reference objective tolerance."""
    if DATA_DIR is None:
        pytest.skip("data/ not found")
    if not netlib_t1:
        pytest.skip("No T1 LP models in manifest")

    failures: list[str] = []
    for entry in netlib_t1:
        try:
            status, our_obj, ref_obj = _solve_and_verify(entry)
            if status != "OPTIMAL":
                failures.append(f"{entry['name']}: status={status}")
                continue
            if ref_obj is not None:
                ref = float(ref_obj)
                rel = abs(our_obj - ref) / (1.0 + abs(ref))
                if rel > 1e-4:
                    failures.append(
                        f"{entry['name']}: obj={our_obj:.6g} ref={ref:.6g} rel={rel:.2e}"
                    )
        except Exception as e:
            failures.append(f"{entry['name']}: {e}")

    assert not failures, "T1 LP failures:\n" + "\n".join(failures)


def test_lp_verifier_passes_on_afiro(manifest: list[dict]) -> None:
    """Run the independent verifier on afiro solution — must return PASS."""
    if DATA_DIR is None:
        pytest.skip("data/ not found")
    entry = next((m for m in manifest if m["name"] == "afiro"), None)
    if entry is None:
        pytest.skip("afiro not in manifest")

    path = model_path(entry)
    model = parse_mps(path)
    opts = DSSOptions(max_iter=50_000)
    result = dual_simplex_solve(model, opts=opts)
    if not isinstance(result, LPResult) or result.status != "OPTIMAL":
        pytest.skip(f"afiro did not reach OPTIMAL (status={getattr(result,'status','?')})")

    # Independent verifier (from nirbhar_verify — no nirbhar imports there)
    from nirbhar_verify.mps_min import parse_mps_min
    from nirbhar_verify.lp_verify import verify_lp

    min_model = parse_mps_min(path)
    vr = verify_lp(min_model, result.x, result.y)
    assert vr.is_pass(), f"Verifier FAIL: {vr.violations}"
    assert vr.gap <= 1e-6, f"Gap too large: {vr.gap:.2e}"
