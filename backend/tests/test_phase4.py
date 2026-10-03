"""
tests/test_phase4.py
====================
Phase 4 test suite: Convex Quadratic Optimization Core (QP & MIQP) (§6.10).
Zero external solver dependencies. 100% sovereign computation.
"""

import math
from pathlib import Path
import numpy as np
import pytest

from nirbhar.io.mps import parse_mps
from nirbhar.lp.dual_simplex import LPResult
from nirbhar.qp.psd import check_psd
from nirbhar.qp.mehrotra_qp import qp_solve, QPOptions
from nirbhar.qp.outer_approx import outer_approximation_miqp, MIQPOptions

_HERE = Path(__file__).resolve().parent
_DATA = _HERE.parent.parent / "data" / "qp"


# ---------------------------------------------------------------------------
# Test Fixtures / Problem Instances
# ---------------------------------------------------------------------------

QP_CONVEX_TEXT = """NAME          QP_CONVEX
ROWS
 N  obj
 L  c1
COLUMNS
    x1        obj        -2.0  c1        1.0
    x2        obj        -3.0  c1        1.0
RHS
    rhs       c1          2.0
BOUNDS
 UP bnd       x1          5.0
 UP bnd       x2          5.0
QUADOBJ
    x1        x1          2.0
    x2        x2          2.0
ENDATA"""

QP_NONCONVEX_TEXT = """NAME          QP_NONCONVEX
ROWS
 N  obj
 L  c1
COLUMNS
    x1        obj        -2.0  c1        1.0
RHS
    rhs       c1          2.0
BOUNDS
 UP bnd       x1          5.0
QUADOBJ
    x1        x1         -2.0
ENDATA"""

MIQP_KNAPSACK_TEXT = """NAME          MIQP_KNAP
ROWS
 N  obj
 L  cap
COLUMNS
    MARK0000  'MARKER'                 'INTORG'
    x1        obj       -10.0  cap       1.0
    x2        obj        -8.0  cap       1.0
    MARK0001  'MARKER'                 'INTDEG'
RHS
    rhs       cap         1.5
BOUNDS
 UP bnd       x1          1.0
 UP bnd       x2          1.0
QUADOBJ
    x1        x1          4.0
    x2        x2          6.0
ENDATA"""


# ---------------------------------------------------------------------------
# 1. PSD Check Unit Tests
# ---------------------------------------------------------------------------

class TestPSD:

    def test_psd_positive_definite(self):
        model = parse_mps(text=QP_CONVEX_TEXT)
        is_psd, msg, q_diag = check_psd(model)
        assert is_psd is True
        assert q_diag is not None
        assert np.all(q_diag >= 0)

    def test_psd_non_convex_refusal(self):
        model = parse_mps(text=QP_NONCONVEX_TEXT)
        is_psd, msg, q_diag = check_psd(model)
        assert is_psd is False
        assert "NON_CONVEX_UNSUPPORTED" in msg

        # Solve should return UNSUPPORTED
        res = qp_solve(model)
        assert res.status == "UNSUPPORTED"


# ---------------------------------------------------------------------------
# 2. Mehrotra Convex QP Solver Tests
# ---------------------------------------------------------------------------

class TestMehrotraQP:

    def test_synthetic_convex_qp(self):
        model = parse_mps(text=QP_CONVEX_TEXT)
        res = qp_solve(model)
        assert res.status == "OPTIMAL"
        assert res.gap <= 1e-5
        # min x1^2 + x2^2 - 2x1 - 3x2 s.t. x1 + x2 <= 2
        # Lagrangian: x1 = 1 - y/2, x2 = 1.5 - y/2, x1 + x2 = 2.5 - y <= 2 => y = 0.5
        # x1 = 0.75, x2 = 1.25. Obj = 0.75^2 + 1.25^2 - 1.5 - 3.75 = 0.5625 + 1.5625 - 5.25 = -3.125
        assert abs(res.z_primal - (-3.125)) < 1e-4

    def test_afiro_qp_diag_benchmark(self):
        path = _DATA / "afiro_qp_diag.mps"
        if not path.exists():
            pytest.skip("afiro_qp_diag.mps not found")
        model = parse_mps(path)
        res = qp_solve(model)
        assert res.status == "OPTIMAL"
        ref_obj = 70.64750820339287
        assert abs(res.z_primal - ref_obj) < 1e-5
        assert res.gap <= 1e-5

    def test_sc50a_qp_diag_benchmark(self):
        path = _DATA / "sc50a_qp_diag.mps"
        if not path.exists():
            pytest.skip("sc50a_qp_diag.mps not found")
        model = parse_mps(path)
        res = qp_solve(model)
        assert res.status == "OPTIMAL"
        ref_obj = -0.004431826858018196
        assert abs(res.z_primal - ref_obj) < 1e-5

    def test_share2b_qp_diag_benchmark(self):
        path = _DATA / "share2b_qp_diag.mps"
        if not path.exists():
            pytest.skip("share2b_qp_diag.mps not found")
        model = parse_mps(path)
        res = qp_solve(model)
        assert res.status == "OPTIMAL"
        ref_obj = 312.4618237198423
        assert abs(res.z_primal - ref_obj) < 1e-4


# ---------------------------------------------------------------------------
# 3. Convex MIQP via Outer Approximation Tests
# ---------------------------------------------------------------------------

class TestConvexMIQP:

    def test_outer_approximation_quadratic_knapsack(self):
        model = parse_mps(text=MIQP_KNAPSACK_TEXT)
        res = outer_approximation_miqp(model, MIQPOptions(verbose=False))
        assert res.status == "OPTIMAL"
        assert abs(res.objective - (-8.0)) < 1e-4
        assert res.gap <= 1e-4
        assert np.allclose(res.x, [1.0, 0.0])
        assert res.cuts_generated >= 1
