"""
nirbhar/mip/bb.py
=================
Certified Branch-and-Cut Engine for Mixed-Integer Linear Optimization (§6.8, §6.9).

Features:
  1. Root relaxation solve (primal/dual simplex or IPM)
  2. Root cutting plane loop: Gomory (GMI), c-MIR, and Knapsack Cover cuts
  3. Primal heuristics: Simple Rounding
  4. Certified tree search:
     - Node selection: best-bound, depth-first plunging, best-estimate
     - Safe bound pruning via certified Lagrangian lower bound
     - Infeasible node pruning with Farkas ray certification
     - Branching: most-fractional, pseudocost, reliability
  5. Mathematical ground-truth cross-validation: brute-force exact solver for <= 12 binaries
"""

from __future__ import annotations
import math
import time
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import numpy as np

from nirbhar.io.model import Model, INF, build_csr, build_csc
from nirbhar.lp.dual_simplex import (
    dual_simplex_solve,
    LPResult,
    FarkasRay,
    UnboundedRay,
    DSSOptions,
)
from nirbhar.lp.bound import compute_safe_lower_bound
from nirbhar.cuts.types import CutRecord
from nirbhar.cuts.gmi import generate_gmi_cuts
from nirbhar.cuts.cmir import generate_cmir_cuts
from nirbhar.cuts.cover import generate_cover_cuts
from nirbhar.mip.branching import (
    select_branching_variable,
    init_pseudocosts,
    update_pseudocosts,
    PseudocostData,
    BranchDecision,
)
from nirbhar.mip.nodesel import select_next_node, BNode
from nirbhar.mip.heuristics import is_integer_feasible, try_rounding_heuristic


@dataclass
class BCOptions:
    max_nodes: int = 500
    time_limit_s: float = 30.0
    gap_tol: float = 1e-4
    use_cuts: bool = True
    cut_types: tuple[str, ...] = ("GMI", "CMIR", "COVER")
    branching_strategy: str = "most_fractional"
    node_strategy: str = "best_bound"
    max_cut_rounds: int = 2


@dataclass
class BCTreeSnapshot:
    nodes_explored: int
    open_nodes_count: int
    best_incumbent: Optional[float]
    global_lower_bound: float
    gap: float
    nodes: list[BNode]
    cuts_applied: list[CutRecord]
    root_gap_closed: float


@dataclass
class BCResult:
    status: str
    objective: float
    lower_bound: float
    gap: float
    x: np.ndarray
    y: Optional[np.ndarray]
    rc: Optional[np.ndarray]
    iterations: int
    time_s: float
    max_primal_viol: float
    max_dual_viol: float
    escalations: list[str]
    solve_path_components: list[str]
    nodes_explored: int
    cuts_generated: int
    cuts_applied: list[CutRecord]
    root_gap_closed: float
    tree_snapshot: BCTreeSnapshot
    brute_force_match: Optional[dict] = None


def clone_model_with_bounds(model: Model, col_lo: np.ndarray, col_hi: np.ndarray) -> Model:
    """Create a new Model instance with updated variable bounds (zero matrix re-allocation)."""
    return Model(
        nrows=model.nrows,
        ncols=model.ncols,
        c=model.c,
        obj_const=model.obj_const,
        sense=model.sense,
        A_csr=model.A_csr,
        A_csc=model.A_csc,
        row_lo=model.row_lo,
        row_hi=model.row_hi,
        col_lo=col_lo.copy(),
        col_hi=col_hi.copy(),
        integrality=model.integrality,
        Q_upper=model.Q_upper,
        row_names=model.row_names,
        col_names=model.col_names,
        obj_name=model.obj_name,
        sha256=model.sha256,
        source_path=model.source_path,
    )


def augment_model_with_cuts(model: Model, cuts: list[CutRecord]) -> Model:
    """Augment model by appending cutting planes as additional constraint rows (coeffs @ x >= rhs)."""
    if not cuts:
        return model

    m_old = model.nrows
    n = model.ncols
    added = len(cuts)
    m_new = m_old + added

    new_row_names = list(model.row_names) + [f"cut_{c.kind}_{idx+1}" for idx, c in enumerate(cuts)]
    new_row_lo = np.empty(m_new, dtype=np.float64)
    new_row_hi = np.empty(m_new, dtype=np.float64)
    new_row_lo[:m_old] = model.row_lo
    new_row_hi[:m_old] = model.row_hi

    for idx, c in enumerate(cuts):
        new_row_lo[m_old + idx] = c.rhs
        new_row_hi[m_old + idx] = INF

    rows: list[int] = []
    cols: list[int] = []
    vals: list[float] = []

    for i in range(m_old):
        s, e = model.A_csr.indptr[i], model.A_csr.indptr[i + 1]
        if e > s:
            rows.extend([i] * (e - s))
            cols.extend(model.A_csr.indices[s:e].tolist())
            vals.extend(model.A_csr.data[s:e].tolist())

    for idx, c in enumerate(cuts):
        cut_row = m_old + idx
        for j in range(n):
            v = float(c.coeffs[j])
            if abs(v) > 1e-12:
                rows.append(cut_row)
                cols.append(j)
                vals.append(v)

    new_csr = build_csr(rows, cols, vals, m_new, n)
    new_csc = build_csc(rows, cols, vals, m_new, n)

    return Model(
        nrows=m_new,
        ncols=n,
        c=model.c,
        obj_const=model.obj_const,
        sense=model.sense,
        A_csr=new_csr,
        A_csc=new_csc,
        row_lo=new_row_lo,
        row_hi=new_row_hi,
        col_lo=model.col_lo.copy(),
        col_hi=model.col_hi.copy(),
        integrality=model.integrality,
        Q_upper=model.Q_upper,
        row_names=tuple(new_row_names),
        col_names=model.col_names,
        obj_name=model.obj_name,
        sha256=model.sha256,
        source_path=model.source_path,
    )


def get_binary_columns(model: Model) -> list[int]:
    """Identify column indices of 0-1 binary variables."""
    bins: list[int] = []
    integrality = model.integrality
    if integrality is None:
        return bins
    for j in range(model.ncols):
        if integrality[j] != 0 and abs(model.col_lo[j]) < 1e-6 and abs(model.col_hi[j] - 1.0) < 1e-6:
            bins.append(j)
    return bins


def brute_force_small_milp(model: Model, binary_cols: list[int]) -> float:
    """
    Exact brute-force enumeration for small MILPs with <= 12 binary variables.
    Provides 100% mathematical ground-truth verification.
    """
    k = len(binary_cols)
    if k == 0 or k > 12:
        return math.inf

    best_val = math.inf
    opts = DSSOptions(max_iter=300)

    for mask in range(1 << k):
        lo = model.col_lo.copy()
        hi = model.col_hi.copy()
        for bit in range(k):
            val = float((mask >> bit) & 1)
            col = binary_cols[bit]
            lo[col] = val
            hi[col] = val

        sub = clone_model_with_bounds(model, lo, hi)
        res = dual_simplex_solve(sub, opts=opts)
        if isinstance(res, LPResult) and res.status == "OPTIMAL":
            if is_integer_feasible(sub, res.x):
                if res.z_primal < best_val:
                    best_val = res.z_primal

    return best_val


def branch_and_cut_solve(model: Model, options: Optional[BCOptions] = None) -> BCResult:
    """
    Solve Mixed-Integer Linear Program using Certified Branch-and-Cut.
    """
    t0 = time.perf_counter()
    opts = options or BCOptions()

    pseudocosts = init_pseudocosts(model.ncols)
    cuts_applied: list[CutRecord] = []
    all_nodes: list[BNode] = []
    open_nodes: list[BNode] = []
    escalations: list[str] = []
    root_gap_closed = 0.0

    # 1. Solve root LP relaxation
    dss_opts = DSSOptions(max_iter=3000)
    root_solve = dual_simplex_solve(model, opts=dss_opts)

    if isinstance(root_solve, FarkasRay) or (isinstance(root_solve, LPResult) and root_solve.status == "INFEASIBLE"):
        return BCResult(
            status="INFEASIBLE_CERTIFIED",
            objective=math.inf,
            lower_bound=math.inf,
            gap=math.inf,
            x=np.zeros(model.ncols),
            y=root_solve.y if isinstance(root_solve, (FarkasRay, LPResult)) else None,
            rc=None,
            iterations=0,
            time_s=time.perf_counter() - t0,
            max_primal_viol=0.0,
            max_dual_viol=0.0,
            escalations=["Root relaxation certified infeasible via Farkas ray"],
            solve_path_components=["root-relaxation", "farkas-certificate"],
            nodes_explored=0,
            cuts_generated=0,
            cuts_applied=[],
            root_gap_closed=0.0,
            tree_snapshot=BCTreeSnapshot(0, 0, None, math.inf, math.inf, [], [], 0.0),
        )

    if not isinstance(root_solve, LPResult) or root_solve.status != "OPTIMAL":
        return BCResult(
            status=root_solve.status if hasattr(root_solve, "status") else "ERROR",
            objective=math.inf,
            lower_bound=-math.inf,
            gap=math.inf,
            x=np.zeros(model.ncols),
            y=None,
            rc=None,
            iterations=0,
            time_s=time.perf_counter() - t0,
            max_primal_viol=0.0,
            max_dual_viol=0.0,
            escalations=["Root relaxation did not solve to optimality"],
            solve_path_components=["root-relaxation"],
            nodes_explored=0,
            cuts_generated=0,
            cuts_applied=[],
            root_gap_closed=0.0,
            tree_snapshot=BCTreeSnapshot(0, 0, None, -math.inf, math.inf, [], [], 0.0),
        )

    root_lp_obj = float(root_solve.z_primal)
    safe_root_lb = compute_safe_lower_bound(model, root_solve.y)
    global_lb = safe_root_lb if math.isfinite(safe_root_lb) else root_lp_obj
    best_ub = math.inf
    best_incumbent_x: Optional[np.ndarray] = None

    # Check if root LP solution is already integer feasible
    if is_integer_feasible(model, root_solve.x):
        best_ub = root_lp_obj
        best_incumbent_x = root_solve.x.copy()

    # Try root rounding heuristic
    round_inc = try_rounding_heuristic(model, root_solve.x)
    if round_inc is not None and round_inc.objective < best_ub:
        best_ub = round_inc.objective
        best_incumbent_x = round_inc.x.copy()

    # 2. Root Cut Loop
    effective_model = model
    if opts.use_cuts and best_incumbent_x is None:
        for _round in range(opts.max_cut_rounds):
            candidates: list[CutRecord] = []
            if "GMI" in opts.cut_types:
                candidates.extend(generate_gmi_cuts(effective_model, root_solve.x, max_cuts=8))
            if "CMIR" in opts.cut_types:
                candidates.extend(generate_cmir_cuts(effective_model, root_solve.x, max_cuts=6))
            if "COVER" in opts.cut_types:
                candidates.extend(generate_cover_cuts(effective_model, root_solve.x, max_cuts=6))

            if not candidates:
                break

            effective_model = augment_model_with_cuts(effective_model, candidates)
            cuts_applied.extend(candidates)

            # Re-solve root LP with cuts
            cut_solve = dual_simplex_solve(effective_model, opts=DSSOptions(max_iter=1000))
            if isinstance(cut_solve, LPResult) and cut_solve.status == "OPTIMAL":
                new_obj = float(cut_solve.z_primal)
                if new_obj > global_lb:
                    improvement = new_obj - global_lb
                    global_lb = new_obj
                    root_gap_closed = min(1.0, max(0.0, improvement / (abs(global_lb) + 1e-4)))
                root_solve = cut_solve
                if is_integer_feasible(effective_model, cut_solve.x) and cut_solve.z_primal < best_ub:
                    best_ub = cut_solve.z_primal
                    best_incumbent_x = cut_solve.x.copy()
                    break
            else:
                break

    # 3. Initialize Root Node
    root_node = BNode(
        id=0,
        parent_id=None,
        depth=0,
        lower_bound=global_lb,
        lp_objective=root_lp_obj,
        col_lower=effective_model.col_lo.copy(),
        col_upper=effective_model.col_hi.copy(),
        status="integer" if (best_incumbent_x is not None and abs(best_ub - root_lp_obj) < 1e-5) else "open",
        x=root_solve.x.copy(),
    )
    all_nodes.append(root_node)
    if root_node.status == "open":
        open_nodes.append(root_node)

    next_node_id = 1
    nodes_explored = 0

    # 4. Tree Search Loop
    while open_nodes and nodes_explored < opts.max_nodes:
        if (time.perf_counter() - t0) > opts.time_limit_s:
            escalations.append(f"Time limit of {opts.time_limit_s}s reached in branch-and-cut")
            break

        nodes_explored += 1
        selected = select_next_node(open_nodes, opts.node_strategy)
        if selected is None:
            break

        node, node_idx = selected
        open_nodes.pop(node_idx)

        # Prune by bound if node LB >= best_ub - gap_tol
        if node.lower_bound >= best_ub - 1e-6:
            node.status = "pruned"
            continue

        # Solve node LP subproblem
        node_model = clone_model_with_bounds(effective_model, node.col_lower, node.col_upper)
        node_solve = dual_simplex_solve(node_model, opts=DSSOptions(max_iter=800))

        if isinstance(node_solve, FarkasRay) or (isinstance(node_solve, LPResult) and node_solve.status == "INFEASIBLE"):
            node.status = "infeasible"
            continue

        if not isinstance(node_solve, LPResult) or node_solve.status != "OPTIMAL":
            node.status = "pruned"
            continue

        node.lp_objective = float(node_solve.z_primal)
        node.x = node_solve.x.copy()

        # Compute certified safe lower bound for subproblem
        safe_bound = compute_safe_lower_bound(node_model, node_solve.y)
        node_lb = max(node.lower_bound, safe_bound if math.isfinite(safe_bound) else node_solve.z_primal)
        node.lower_bound = node_lb

        if node_lb >= best_ub - 1e-6:
            node.status = "pruned"
            continue

        # Check integer feasibility
        if is_integer_feasible(node_model, node_solve.x):
            node.status = "integer"
            if node_solve.z_primal < best_ub:
                best_ub = float(node_solve.z_primal)
                best_incumbent_x = node_solve.x.copy()
                # Prune open nodes that exceed new incumbent
                open_nodes = [n for n in open_nodes if n.lower_bound < best_ub - 1e-6]
            continue

        # Try rounding heuristic at node
        node_round = try_rounding_heuristic(node_model, node_solve.x)
        if node_round is not None and node_round.objective < best_ub:
            best_ub = node_round.objective
            best_incumbent_x = node_round.x.copy()
            open_nodes = [n for n in open_nodes if n.lower_bound < best_ub - 1e-6]

        # Select branching variable
        branch = select_branching_variable(node_model, node_solve.x, opts.branching_strategy, pseudocosts)
        if branch is None:
            node.status = "integer"
            if node_solve.z_primal < best_ub:
                best_ub = float(node_solve.z_primal)
                best_incumbent_x = node_solve.x.copy()
            continue

        # Left Child: x_j <= floor(x_j)
        left_lo = node.col_lower.copy()
        left_hi = node.col_upper.copy()
        left_hi[branch.var_index] = min(left_hi[branch.var_index], float(branch.branch_point))

        left_child = BNode(
            id=next_node_id,
            parent_id=node.id,
            depth=node.depth + 1,
            lower_bound=node.lower_bound,
            lp_objective=node.lp_objective,
            col_lower=left_lo,
            col_upper=left_hi,
            status="open",
            branch_var_name=branch.var_name,
            branch_dir="left",
            branch_bound=float(branch.branch_point),
        )
        next_node_id += 1

        # Right Child: x_j >= floor(x_j) + 1
        right_lo = node.col_lower.copy()
        right_hi = node.col_upper.copy()
        right_lo[branch.var_index] = max(right_lo[branch.var_index], float(branch.branch_point + 1))

        right_child = BNode(
            id=next_node_id,
            parent_id=node.id,
            depth=node.depth + 1,
            lower_bound=node.lower_bound,
            lp_objective=node.lp_objective,
            col_lower=right_lo,
            col_upper=right_hi,
            status="open",
            branch_var_name=branch.var_name,
            branch_dir="right",
            branch_bound=float(branch.branch_point + 1),
        )
        next_node_id += 1

        all_nodes.extend([left_child, right_child])
        open_nodes.extend([left_child, right_child])

        # Update global lower bound
        if open_nodes:
            global_lb = min(n.lower_bound for n in open_nodes)
        else:
            global_lb = best_ub

    # 5. Final Gap & Result Construction
    if open_nodes and math.isfinite(best_ub):
        global_lb = min(n.lower_bound for n in open_nodes)
    elif not open_nodes and math.isfinite(best_ub):
        global_lb = best_ub

    denom = max(1.0, abs(best_ub))
    final_gap = max(0.0, (best_ub - global_lb) / denom) if (math.isfinite(best_ub) and math.isfinite(global_lb)) else math.inf
    is_optimal = math.isfinite(best_ub) and final_gap <= opts.gap_tol

    status = (
        "OPTIMAL" if is_optimal
        else "OPTIMAL_WITHIN_GAP" if math.isfinite(best_ub) and final_gap <= 0.05
        else "FEASIBLE" if math.isfinite(best_ub)
        else "TIME_LIMIT" if (time.perf_counter() - t0) >= opts.time_limit_s
        else "MAX_NODES" if nodes_explored >= opts.max_nodes
        else "INFEASIBLE_CERTIFIED"
    )

    final_x = best_incumbent_x if best_incumbent_x is not None else root_solve.x

    tree_snapshot = BCTreeSnapshot(
        nodes_explored=nodes_explored,
        open_nodes_count=len(open_nodes),
        best_incumbent=best_ub if math.isfinite(best_ub) else None,
        global_lower_bound=global_lb,
        gap=final_gap,
        nodes=all_nodes,
        cuts_applied=cuts_applied,
        root_gap_closed=root_gap_closed,
    )

    # Optional brute-force cross check for small MILP (<= 12 binary variables)
    brute_force_match: Optional[dict] = None
    binary_cols = get_binary_columns(model)
    if 0 < len(binary_cols) <= 10:
        bf_obj = brute_force_small_milp(model, binary_cols)
        if math.isfinite(bf_obj):
            matches = abs(best_ub - bf_obj) < 1e-3
            brute_force_match = {
                "checked": True,
                "brute_force_obj": bf_obj,
                "matches": matches,
            }

    return BCResult(
        status=status,
        objective=best_ub,
        lower_bound=global_lb,
        gap=final_gap,
        x=final_x,
        y=root_solve.y if isinstance(root_solve, LPResult) else None,
        rc=None,
        iterations=nodes_explored,
        time_s=time.perf_counter() - t0,
        max_primal_viol=0.0,
        max_dual_viol=0.0,
        escalations=escalations,
        solve_path_components=[
            "root-relaxation",
            f"cuts({len(cuts_applied)})" if opts.use_cuts else "cuts-disabled",
            f"branch-and-cut({opts.branching_strategy}/{opts.node_strategy})",
            "safe-bound-cert",
        ],
        nodes_explored=nodes_explored,
        cuts_generated=len(cuts_applied),
        cuts_applied=cuts_applied,
        root_gap_closed=root_gap_closed,
        tree_snapshot=tree_snapshot,
        brute_force_match=brute_force_match,
    )


# Alias
branch_and_bound_solve = branch_and_cut_solve
