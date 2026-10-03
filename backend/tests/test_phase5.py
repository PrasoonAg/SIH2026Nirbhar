"""
tests/test_phase5.py
====================
Phase 5 test suite: Explainability, Infeasibility Diagnostics (IIS, Farkas), and Certificates (§6.7, §7).
Zero external solver dependencies. 100% sovereign computation.
"""

import json
from pathlib import Path
import numpy as np
import pytest

from nirbhar.io.mps import parse_mps
from nirbhar.lp.dual_simplex import dual_simplex_solve, LPResult, FarkasRay
from nirbhar.explain.farkas import certify_farkas_ray
from nirbhar.explain.iis import compute_iis
from nirbhar.explain.report import generate_explanation_report
from nirbhar.certificate.builder import build_certificate
from nirbhar_verify.mps_min import parse_mps_min
from nirbhar_verify.lp_verify import verify_lp

_HERE = Path(__file__).resolve().parent
_DATA = _HERE.parent.parent / "data"

INFEAS_MODEL = """NAME          INFEAS_TEST
ROWS
 N  obj
 G  c_min
 L  c_max
COLUMNS
    x1        obj        1.0   c_min      1.0   c_max      1.0
RHS
    rhs       c_min     10.0   c_max      5.0
BOUNDS
 UP bnd       x1        20.0
ENDATA"""

FEAS_MODEL = """NAME          FEAS_TEST
ROWS
 N  obj
 L  cap
COLUMNS
    x1        obj       -2.0   cap        1.0
RHS
    rhs       cap        5.0
BOUNDS
 UP bnd       x1        10.0
ENDATA"""


# ---------------------------------------------------------------------------
# 1. Farkas Ray Certification Tests
# ---------------------------------------------------------------------------

class TestFarkasRay:

    def test_farkas_ray_on_infeasible_lp(self):
        model = parse_mps(text=INFEAS_MODEL)
        res = dual_simplex_solve(model)
        assert isinstance(res, (FarkasRay, LPResult))

        ray = res.y
        assert ray is not None
        cert = certify_farkas_ray(model, ray)
        assert cert.is_valid is True
        assert cert.farkas_value > 0.0
        assert cert.max_dual_violation <= 1e-6


# ---------------------------------------------------------------------------
# 2. Irreducible Infeasible Subsystem (IIS) Tests
# ---------------------------------------------------------------------------

class TestIIS:

    def test_iis_on_infeasible_model(self):
        model = parse_mps(text=INFEAS_MODEL)
        iis = compute_iis(model)
        assert iis.is_infeasible is True
        assert len(iis.iis_row_indices) > 0
        assert "c_min" in iis.iis_row_names or "c_max" in iis.iis_row_names

    def test_iis_on_feasible_model(self):
        model = parse_mps(text=FEAS_MODEL)
        iis = compute_iis(model)
        assert iis.is_infeasible is False
        assert len(iis.iis_row_indices) == 0


# ---------------------------------------------------------------------------
# 3. Explainability Report Tests
# ---------------------------------------------------------------------------

class TestExplainReport:

    def test_explain_optimal_report(self):
        model = parse_mps(text=FEAS_MODEL)
        res = dual_simplex_solve(model)
        report = generate_explanation_report(model, res, timing_s=0.01)
        assert "[OPTIMAL]" in report.headline
        assert len(report.sections) >= 2

    def test_explain_infeasible_report(self):
        model = parse_mps(text=INFEAS_MODEL)
        res = dual_simplex_solve(model)
        report = generate_explanation_report(model, res, timing_s=0.01)
        assert "[INFEASIBLE]" in report.headline
        assert any(sec.title == "Conflict Diagnosis (IIS)" for sec in report.sections)


# ---------------------------------------------------------------------------
# 4. Certificate Builder & Standalone Verifier Integration Tests
# ---------------------------------------------------------------------------

class TestCertificateAndVerifier:

    def test_build_and_verify_certificate(self):
        # 1. Solve model
        path = _DATA / "netlib" / "afiro.mps"
        if not path.exists():
            pytest.skip("afiro.mps not found")

        model = parse_mps(path)
        res = dual_simplex_solve(model)
        assert isinstance(res, LPResult)
        assert res.status == "OPTIMAL"

        # 2. Build certificate
        cert = build_certificate(model, res, timing_s=0.05, solve_path=["primal-simplex"])
        assert cert["status"] == "OPTIMAL"
        assert "objective" in cert
        assert "bound" in cert

        # Certificate JSON serialization check
        cert_json = json.dumps(cert, indent=2)
        assert len(cert_json) > 100

        # 3. Independent verifier verification (isolated package)
        min_model = parse_mps_min(path)
        v_res = verify_lp(min_model, res.x, res.y)
        assert v_res.is_pass()
        assert bool(v_res.primal_feas)
        assert bool(v_res.dual_feas)
