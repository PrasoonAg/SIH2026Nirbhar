"""
nirbhar/certificate/builder.py
================================
JSON certificate builder for NIRBHAR solver results.

Generates structured certificate.json adhering to the NIRBHAR schema:
  schema_version  : str
  status          : "OPTIMAL" | "INFEASIBLE" | "UNBOUNDED" | "MAX_ITER" | "NUMERICAL"
  model           : { name, sha256, nrows, ncols, nnz, class_ }
  objective       : { primal, dual, sense }
  bound           : { lb, margin, safe_lb }
  gap             : relative duality gap
  violations      : list of violation strings
  hardware        : { platform, cpu, python_version }
  solve_path      : list of phases used ("PHASE1", "PHASE2", etc.)
  timing_s        : wall-clock seconds
  verifier        : { status, msg } | null

Sovereignty: no external solver imports. Uses only stdlib + NumPy.
"""

from __future__ import annotations

import json
import platform
import time
from typing import Optional, Any

import numpy as np

from nirbhar.io.model import Model
from nirbhar.lp.dual_simplex import LPResult, FarkasRay, UnboundedRay
from nirbhar.certificate.safe_bound import safe_lower_bound


SCHEMA_VERSION = "1.0.0"


def build_certificate(
    model: Model,
    result: Any,                       # LPResult | FarkasRay | UnboundedRay
    timing_s: float = 0.0,
    solve_path: Optional[list[str]] = None,
    verifier_result: Optional[Any] = None,   # VerifyResult from nirbhar_verify (optional)
) -> dict:
    """
    Build a NIRBHAR certificate dict from a solve result.

    Parameters
    ----------
    model           : The solved Model.
    result          : Solve result (LPResult / FarkasRay / UnboundedRay).
    timing_s        : Wall-clock solve time in seconds.
    solve_path      : List of solver phases used.
    verifier_result : Optional VerifyResult from independent verifier.

    Returns
    -------
    dict  (JSON-serializable)
    """
    if solve_path is None:
        solve_path = ["PHASE1", "PHASE2"] if isinstance(result, LPResult) else ["PHASE1"]

    # ── Model metadata ────────────────────────────────────────────────────────
    model_info = {
        "name": getattr(model, "obj_name", "unknown"),
        "sha256": model.sha256,
        "nrows": model.nrows,
        "ncols": model.ncols,
        "nnz": model.nnz,
        "class_": model.problem_class,
        "sense": model.sense,
    }

    # ── Hardware ──────────────────────────────────────────────────────────────
    hardware = {
        "platform": platform.platform(),
        "cpu": platform.processor() or platform.machine(),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
    }

    # ── Status-specific fields ────────────────────────────────────────────────
    if isinstance(result, LPResult) and result.status == "OPTIMAL":
        lb, margin = safe_lower_bound(model, result.y)

        cert = {
            "schema_version": SCHEMA_VERSION,
            "status": "OPTIMAL",
            "model": model_info,
            "objective": {
                "primal": float(result.z_primal),
                "dual": float(result.z_dual),
                "sense": model.sense,
            },
            "bound": {
                "lb": float(lb),
                "margin": float(margin),
                "safe_lb": float(lb - margin),
            },
            "gap": float(result.gap),
            "solution": {
                "x": [float(v) for v in result.x],
                "y": [float(v) for v in result.y],
            },
            "violations": [],
            "hardware": hardware,
            "solve_path": solve_path,
            "timing_s": float(timing_s),
            "iters": result.iters,
            "verifier": _encode_verifier(verifier_result),
        }

    elif isinstance(result, FarkasRay) or (isinstance(result, LPResult) and result.status == "INFEASIBLE"):
        cert = {
            "schema_version": SCHEMA_VERSION,
            "status": "INFEASIBLE",
            "model": model_info,
            "objective": None,
            "bound": None,
            "gap": None,
            "violations": ["Primal infeasible (Farkas ray)"],
            "hardware": hardware,
            "solve_path": solve_path,
            "timing_s": float(timing_s),
            "iters": getattr(result, "iters", 0),
            "verifier": _encode_verifier(verifier_result),
        }

    elif isinstance(result, UnboundedRay) or (isinstance(result, LPResult) and result.status == "UNBOUNDED"):
        cert = {
            "schema_version": SCHEMA_VERSION,
            "status": "UNBOUNDED",
            "model": model_info,
            "objective": None,
            "bound": None,
            "gap": None,
            "violations": ["Primal unbounded ray"],
            "hardware": hardware,
            "solve_path": solve_path,
            "timing_s": float(timing_s),
            "iters": getattr(result, "iters", 0),
            "verifier": _encode_verifier(verifier_result),
        }

    else:
        # MAX_ITER / NUMERICAL / other
        status = getattr(result, "status", "UNKNOWN")
        cert = {
            "schema_version": SCHEMA_VERSION,
            "status": status,
            "model": model_info,
            "objective": None,
            "bound": None,
            "gap": None,
            "violations": [getattr(result, "msg", "")],
            "hardware": hardware,
            "solve_path": solve_path,
            "timing_s": float(timing_s),
            "iters": getattr(result, "iters", 0),
            "verifier": None,
        }

    return cert


def write_certificate(
    cert: dict,
    path: str = "certificate.json",
    indent: int = 2,
) -> None:
    """Write certificate dict to a JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cert, f, indent=indent, ensure_ascii=False)


def solve_and_certify(
    model: Model,
    opts=None,
    verifier_result: Optional[Any] = None,   # pre-computed VerifyResult from external call
) -> tuple[Any, dict]:
    """
    Solve model and build a JSON certificate.

    Parameters
    ----------
    model           : Model to solve.
    opts            : DSSOptions (optional).
    verifier_result : Pre-computed VerifyResult from nirbhar_verify (caller's responsibility).
                      nirbhar/ cannot import nirbhar_verify/ — sovereignty rule.

    Returns
    -------
    (result, cert) : (LPResult/FarkasRay/UnboundedRay, certificate dict)
    """
    from nirbhar.lp.dual_simplex import dual_simplex_solve, DSSOptions

    if opts is None:
        opts = DSSOptions()

    t0 = time.perf_counter()
    result = dual_simplex_solve(model, opts=opts)
    timing_s = time.perf_counter() - t0

    # NOTE: verification must be run externally by the caller (from nirbhar_verify)
    # and passed back in.  nirbhar/ CANNOT import nirbhar_verify/ — sovereignty rule.
    verifier_result = None

    cert = build_certificate(
        model=model,
        result=result,
        timing_s=timing_s,
        solve_path=["PHASE1", "PHASE2"],
        verifier_result=verifier_result,
    )

    return result, cert


def _encode_verifier(verifier_result: Optional[Any]) -> Optional[dict]:
    """Encode a VerifyResult (from nirbhar_verify) into the certificate."""
    if verifier_result is None:
        return None
    return {
        "status": getattr(verifier_result, "status", "UNKNOWN"),
        "gap": float(getattr(verifier_result, "gap", float("nan"))),
        "primal_obj": float(getattr(verifier_result, "primal_obj", float("nan"))),
        "dual_obj": float(getattr(verifier_result, "dual_obj", float("nan"))),
        "violations": list(getattr(verifier_result, "violations", [])),
        "msg": str(getattr(verifier_result, "msg", "")),
    }
