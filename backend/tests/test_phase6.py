"""
tests/test_phase6.py
====================
Phase 6 test suite: Industrial Refinery Models and CLI Integration (§6.11).
Zero external solver dependencies. 100% sovereign computation.
"""

from pathlib import Path
import json
import pytest

from nirbhar.industrial.refinery import build_refinery_model
from nirbhar.lp.dual_simplex import dual_simplex_solve, LPResult
from nirbhar.qp.mehrotra_qp import qp_solve
from nirbhar.mip.bb import branch_and_cut_solve, BCOptions
from nirbhar.cli import main as cli_main
from nirbhar_verify.cli import main as verify_cli_main

_HERE = Path(__file__).resolve().parent
_DATA = _HERE.parent.parent / "data"


# ---------------------------------------------------------------------------
# 1. Industrial Model Generation & Solves
# ---------------------------------------------------------------------------

class TestRefineryModels:

    def test_refinery_lp_solve(self):
        model = build_refinery_model(periods=4, problem_class="LP", scenario="baseline")
        assert model.nrows == 32
        assert model.ncols == 72
        assert model.is_lp is True

        res = dual_simplex_solve(model)
        assert isinstance(res, LPResult)
        assert res.status == "OPTIMAL"
        # Objective is -GRM (revenue - cost)
        grm = -res.z_primal
        assert grm > 5000.0  # Positive gross refining margin

    def test_refinery_qp_solve(self):
        model = build_refinery_model(periods=4, problem_class="QP", scenario="baseline")
        assert model.is_qp is True
        assert model.Q_upper is not None

        res = qp_solve(model)
        assert res.status == "OPTIMAL"
        grm = -res.z_primal
        assert grm > 5000.0

    def test_refinery_milp_solve(self):
        model = build_refinery_model(periods=2, problem_class="MILP", scenario="baseline")
        assert model.is_milp is True
        assert model.n_integers == 2

        res = branch_and_cut_solve(model, BCOptions(max_nodes=50))
        assert res.status == "OPTIMAL"
        grm = -res.objective
        assert grm > 1000.0


# ---------------------------------------------------------------------------
# 2. CLI Integration Tests
# ---------------------------------------------------------------------------

class TestCLI:

    def test_cli_solve_and_verify(self, tmp_path):
        mps_file = _DATA / "netlib" / "afiro.mps"
        if not mps_file.exists():
            pytest.skip("afiro.mps not found")

        cert_file = tmp_path / "test_cert.json"

        # 1. Solve
        ret_solve = cli_main(["solve", str(mps_file), "--cert", str(cert_file)])
        assert ret_solve == 0
        assert cert_file.exists()

        # 2. Verify
        ret_verify = cli_main(["verify", str(mps_file), str(cert_file)])
        assert ret_verify == 0

        # 3. Verify via independent verifier CLI
        ret_indep_verify = verify_cli_main([str(mps_file), str(cert_file)])
        assert ret_indep_verify == 0

    def test_cli_industrial(self):
        ret = cli_main(["industrial", "--periods", "2", "--class", "LP"])
        assert ret == 0

    def test_cli_bench(self):
        ret = cli_main(["bench", "--tier", "qp", "--limit", "2"])
        assert ret == 0
