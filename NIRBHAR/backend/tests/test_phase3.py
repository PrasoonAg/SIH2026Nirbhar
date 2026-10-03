"""
tests/test_phase3.py
====================
Phase 3 test suite: Cutting Planes, Branching, Node Selection, and Certified Branch-and-Cut (§6.8, §6.9).
Zero external solver dependencies. 100% sovereign computation.
"""

import math
import numpy as np
import pytest

from nirbhar.io.mps import parse_mps
from nirbhar.io.model import Model
from nirbhar.lp.dual_simplex import dual_simplex_solve, LPResult
from nirbhar.cuts.types import CutRecord
from nirbhar.cuts.gmi import generate_gmi_cuts
from nirbhar.cuts.cmir import generate_cmir_cuts
from nirbhar.cuts.cover import generate_cover_cuts
from nirbhar.mip.branching import (
    select_branching_variable,
    init_pseudocosts,
    update_pseudocosts,
    PseudocostData,
)
from nirbhar.mip.nodesel import select_next_node, BNode
from nirbhar.mip.heuristics import is_integer_feasible, try_rounding_heuristic
from nirbhar.mip.bb import (
    branch_and_cut_solve,
    brute_force_small_milp,
    augment_model_with_cuts,
    BCOptions,
)


# ---------------------------------------------------------------------------
# Test Fixtures / Problem Instances
# ---------------------------------------------------------------------------

KNAPSACK_3 = """NAME          KNAP3
ROWS
 N  obj
 L  cap
COLUMNS
    MARK0000  'MARKER'                 'INTORG'
    x1        obj       -10.0  cap       5.0
    x2        obj       -8.0   cap       4.0
    x3        obj       -5.0   cap       3.0
    MARK0001  'MARKER'                 'INTDEG'
RHS
    rhs       cap       7.0
BOUNDS
 UP bnd       x1        1.0
 UP bnd       x2        1.0
 UP bnd       x3        1.0
ENDATA"""

KNAPSACK_5 = """NAME          KNAP5
ROWS
 N  obj
 L  cap
COLUMNS
    MARK0000  'MARKER'                 'INTORG'
    x1        obj       -15.0  cap       6.0
    x2        obj       -12.0  cap       5.0
    x3        obj       -9.0   cap       4.0
    x4        obj       -16.0  cap       7.0
    x5        obj       -6.0   cap       3.0
    MARK0001  'MARKER'                 'INTDEG'
RHS
    rhs       cap       12.0
BOUNDS
 UP bnd       x1        1.0
 UP bnd       x2        1.0
 UP bnd       x3        1.0
 UP bnd       x4        1.0
 UP bnd       x5        1.0
ENDATA"""

MIXED_MIP = """NAME          MIXED_MIP
ROWS
 N  obj
 G  demand
 L  setup
COLUMNS
    MARK0000  'MARKER'                 'INTORG'
    y         obj        10.0  setup    -100.0
    MARK0001  'MARKER'                 'INTDEG'
    x1        obj         2.0  demand      1.0   setup   1.0
    x2        obj         3.0  demand      1.0   setup   1.0
RHS
    rhs       demand     10.0
BOUNDS
 UP bnd       y           1.0
ENDATA"""

INFEASIBLE_MILP = """NAME          INFEAS_MILP
ROWS
 N  obj
 G  c1
 L  c2
COLUMNS
    MARK0000  'MARKER'                 'INTORG'
    x1        obj         1.0  c1          1.0   c2      1.0
    MARK0001  'MARKER'                 'INTDEG'
RHS
    rhs       c1          3.0  c2          2.0
BOUNDS
 UP bnd       x1          5.0
ENDATA"""


# ---------------------------------------------------------------------------
# 1. Cutting Planes Unit Tests
# ---------------------------------------------------------------------------

class TestCuttingPlanes:

    def test_gmi_cut_generation(self):
        model = parse_mps(text=KNAPSACK_3)
        res = dual_simplex_solve(model)
        assert isinstance(res, LPResult)
        assert res.status == "OPTIMAL"

        cuts = generate_gmi_cuts(model, res.x, min_fractionality=0.01)
        assert isinstance(cuts, list)
        for cut in cuts:
            assert isinstance(cut, CutRecord)
            assert cut.kind == "GMI"
            assert len(cut.coeffs) == model.ncols
            # LP solution must violate cut: cut.coeffs @ res.x < cut.rhs
            assert cut.lp_value < cut.rhs + 1e-5

    def test_cmir_cut_generation(self):
        model = parse_mps(text=KNAPSACK_3)
        res = dual_simplex_solve(model)
        cuts = generate_cmir_cuts(model, res.x, min_fractionality=0.01)
        assert isinstance(cuts, list)
        for cut in cuts:
            assert cut.kind == "CMIR"
            assert cut.lp_value < cut.rhs + 1e-5

    def test_cover_cut_generation(self):
        model = parse_mps(text=KNAPSACK_3)
        res = dual_simplex_solve(model)
        cuts = generate_cover_cuts(model, res.x)
        assert isinstance(cuts, list)
        for cut in cuts:
            assert cut.kind == "COVER"
            assert cut.lp_value < cut.rhs + 1e-5

    def test_augment_model_with_cuts(self):
        model = parse_mps(text=KNAPSACK_3)
        res = dual_simplex_solve(model)
        cuts = generate_gmi_cuts(model, res.x, min_fractionality=0.01)
        if cuts:
            augmented = augment_model_with_cuts(model, cuts)
            assert augmented.nrows == model.nrows + len(cuts)
            assert augmented.ncols == model.ncols
            # Solving augmented LP should be feasible and lower bound should be >= original
            aug_res = dual_simplex_solve(augmented)
            assert isinstance(aug_res, LPResult)
            assert aug_res.status == "OPTIMAL"
            assert aug_res.z_primal >= res.z_primal - 1e-6


# ---------------------------------------------------------------------------
# 2. Branching & Node Selection Unit Tests
# ---------------------------------------------------------------------------

class TestBranchingAndNodeSelection:

    def test_branching_most_fractional(self):
        model = parse_mps(text=KNAPSACK_3)
        x_frac = np.array([0.9, 0.51, 0.1])
        branch = select_branching_variable(model, x_frac, strategy="most_fractional")
        assert branch is not None
        assert branch.var_index == 1  # 0.51 is closest to 0.5
        assert branch.branch_point == 0

    def test_branching_pseudocosts(self):
        model = parse_mps(text=KNAPSACK_3)
        pc = init_pseudocosts(model.ncols)
        # Give var 0 very high pseudocost
        update_pseudocosts(pc, 0, "up", delta_obj=10.0, fractional_dist=0.5)
        update_pseudocosts(pc, 0, "down", delta_obj=10.0, fractional_dist=0.5)

        x_frac = np.array([0.45, 0.50, 0.48])
        branch = select_branching_variable(model, x_frac, strategy="pseudocost", pseudocosts=pc)
        assert branch is not None
        assert branch.var_index == 0

    def test_branching_reliability(self):
        model = parse_mps(text=KNAPSACK_3)
        pc = init_pseudocosts(model.ncols)
        # var 0 has 5 updates (reliable), var 1 has 0 updates (unreliable)
        for _ in range(5):
            update_pseudocosts(pc, 0, "up", delta_obj=1.0, fractional_dist=0.5)
            update_pseudocosts(pc, 0, "down", delta_obj=1.0, fractional_dist=0.5)

        x_frac = np.array([0.5, 0.5, 0.5])
        branch = select_branching_variable(model, x_frac, strategy="reliability", pseudocosts=pc)
        assert branch is not None
        # Unreliable variables (count < 4) are prioritized
        assert branch.var_index in (1, 2)

    def test_node_selection_strategies(self):
        nodes = [
            BNode(id=1, parent_id=0, depth=1, lower_bound=10.0, lp_objective=10.0,
                  col_lower=np.zeros(2), col_upper=np.ones(2)),
            BNode(id=2, parent_id=0, depth=3, lower_bound=15.0, lp_objective=15.0,
                  col_lower=np.zeros(2), col_upper=np.ones(2)),
            BNode(id=3, parent_id=0, depth=2, lower_bound=8.0, lp_objective=8.0,
                  col_lower=np.zeros(2), col_upper=np.ones(2)),
        ]

        # best_bound picks min lower bound (node id=3, lb=8.0)
        sel_bb, idx_bb = select_next_node(nodes, strategy="best_bound")
        assert sel_bb.id == 3
        assert idx_bb == 2

        # depth_first picks deepest node (node id=2, depth=3)
        sel_df, idx_df = select_next_node(nodes, strategy="depth_first")
        assert sel_df.id == 2
        assert idx_df == 1


# ---------------------------------------------------------------------------
# 3. Primal Heuristics Unit Tests
# ---------------------------------------------------------------------------

class TestPrimalHeuristics:

    def test_is_integer_feasible(self):
        model = parse_mps(text=KNAPSACK_3)
        assert is_integer_feasible(model, np.array([1.0, 0.0, 1.0])) is True
        assert is_integer_feasible(model, np.array([1.0, 0.00001, 1.0])) is True
        assert is_integer_feasible(model, np.array([1.0, 0.5, 0.0])) is False

    def test_try_rounding_heuristic(self):
        model = parse_mps(text=KNAPSACK_3)
        # x = [0.1, 0.1, 0.1] -> rounds to [0, 0, 0], which satisfies capacity 0 <= 7
        inc = try_rounding_heuristic(model, np.array([0.1, 0.1, 0.1]))
        assert inc is not None
        assert np.allclose(inc.x, [0.0, 0.0, 0.0])
        assert inc.objective == 0.0


# ---------------------------------------------------------------------------
# 4. Branch-and-Cut Integration & Brute-Force Agreement Tests
# ---------------------------------------------------------------------------

class TestBranchAndCutEngine:

    def test_knapsack3_optimality_and_brute_force(self):
        model = parse_mps(text=KNAPSACK_3)
        bf_obj = brute_force_small_milp(model, [0, 1, 2])
        assert abs(bf_obj - (-13.0)) < 1e-4

        res = branch_and_cut_solve(model, BCOptions(use_cuts=True))
        assert res.status == "OPTIMAL"
        assert abs(res.objective - bf_obj) < 1e-4
        assert res.gap <= 1e-4
        assert np.allclose(res.x, [0.0, 1.0, 1.0])
        assert res.brute_force_match is not None
        assert res.brute_force_match["matches"] is True

    def test_knapsack5_all_branching_and_node_selection(self):
        model = parse_mps(text=KNAPSACK_5)
        bf_obj = brute_force_small_milp(model, [0, 1, 2, 3, 4])
        assert abs(bf_obj - (-28.0)) < 1e-4

        for bs in ["most_fractional", "pseudocost", "reliability"]:
            for ns in ["best_bound", "depth_first", "best_estimate"]:
                res = branch_and_cut_solve(
                    model,
                    BCOptions(branching_strategy=bs, node_strategy=ns, use_cuts=True),
                )
                assert res.status == "OPTIMAL"
                assert abs(res.objective - bf_obj) < 1e-4
                assert res.gap <= 1e-4

    def test_mixed_integer_programming(self):
        model = parse_mps(text=MIXED_MIP)
        res = branch_and_cut_solve(model, BCOptions(use_cuts=True))
        assert res.status == "OPTIMAL"
        assert abs(res.objective - 30.0) < 1e-4
        assert res.gap <= 1e-4
        # y should be binary 1.0, demand met
        assert abs(res.x[0] - 1.0) < 1e-4
        assert res.x[1] + res.x[2] >= 10.0 - 1e-4

    def test_infeasible_milp_detection(self):
        model = parse_mps(text=INFEASIBLE_MILP)
        res = branch_and_cut_solve(model)
        assert res.status in ("INFEASIBLE_CERTIFIED", "INFEASIBLE")
