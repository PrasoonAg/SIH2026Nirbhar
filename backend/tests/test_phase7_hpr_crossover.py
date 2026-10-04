"""
tests/test_phase7_hpr_crossover.py
==================================
Tests for JAX/CPU HPR Solver, Basis Crossover, Concurrent Root Race, and Parallel B&C.
Zero external solver dependencies. 100% sovereign computation.
"""

from pathlib import Path
import numpy as np
import pytest

from nirbhar.io.mps import parse_mps
from nirbhar.hpr.hpr_solver import hpr_solve, hpr_batch_solve, HPROptions, BatchScenario
from nirbhar.crossover.crossover import crossover_solve, CrossoverOptions
from nirbhar.robust.controller import concurrent_root_race, dispatch_solve
from nirbhar.mip.parallel_bb import parallel_branch_and_cut_solve, ParallelBCOptions
from nirbhar.industrial.refinery import build_refinery_model

_HERE = Path(__file__).resolve().parent
_DATA = _HERE.parent.parent / "data"


def test_hpr_afiro_solve():
    """Test HPR first-order solver on Netlib AFIRO."""
    afiro_path = _DATA / "netlib" / "afiro.mps"
    if not afiro_path.exists():
        pytest.skip("afiro.mps not found")

    model = parse_mps(afiro_path)
    opts = HPROptions(max_iter=1500, tol=1e-4)
    res = hpr_solve(model, opts)
    assert res.status in ("OPTIMAL", "CONVERGED", "CERTIFIED_APPROXIMATE", "SUBOPTIMAL")
    # Crossover polishes the solution to exact optimum
    xo = crossover_solve(model, res.x, res.y)
    assert xo.status == "OPTIMAL"
    assert abs(xo.z_primal - (-464.75314)) < 1e-3


def test_hpr_basis_crossover():
    """Test Basis Crossover from HPR continuous iterate to vertex basic solution."""
    afiro_path = _DATA / "netlib" / "afiro.mps"
    if not afiro_path.exists():
        pytest.skip("afiro.mps not found")

    model = parse_mps(afiro_path)
    hpr_res = hpr_solve(model, HPROptions(max_iter=1500, tol=1e-3))
    xo_res = crossover_solve(model, hpr_res.x, hpr_res.y)

    assert xo_res.status == "OPTIMAL"
    assert xo_res.is_vertex_basic is True
    # Published AFIRO optimum is -464.75314
    assert abs(xo_res.z_primal - (-464.75314)) < 1e-3
    assert len(xo_res.basic_vars) == model.nrows


def test_hpr_batch_scenarios():
    """Test batched scenario optimization using HPR."""
    afiro_path = _DATA / "netlib" / "afiro.mps"
    if not afiro_path.exists():
        pytest.skip("afiro.mps not found")

    model = parse_mps(afiro_path)
    scenarios = [
        BatchScenario(scenario_id="sc_base"),
        BatchScenario(scenario_id="sc_perturb_cost", cost_perturbation=np.ones(model.ncols) * 0.1),
        BatchScenario(scenario_id="sc_perturb_rhs", rhs_perturbation=np.ones(model.nrows) * 0.05),
    ]
    batch_res = hpr_batch_solve(model, scenarios, HPROptions(max_iter=500))
    assert batch_res.scenarios_solved == 3
    assert len(batch_res.results) == 3


def test_concurrent_root_race():
    """Test concurrent root race across Simplex, IPM, and HPR."""
    afiro_path = _DATA / "netlib" / "afiro.mps"
    if not afiro_path.exists():
        pytest.skip("afiro.mps not found")

    model = parse_mps(afiro_path)
    race_res = concurrent_root_race(model, timeout_s=30.0)
    assert race_res.status == "OPTIMAL"
    assert race_res.inner.status == "OPTIMAL"


def test_parallel_branch_and_cut():
    """Test deterministic parallel branch-and-cut on refinery MILP."""
    model = build_refinery_model(periods=2, problem_class="MILP", scenario="baseline")
    opts = ParallelBCOptions(num_workers=2, max_nodes=50)
    res = parallel_branch_and_cut_solve(model, opts)
    assert res.status == "OPTIMAL"
    assert res.objective < 0.0  # Maximizing GRM means negative min obj
