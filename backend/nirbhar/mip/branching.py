"""
nirbhar/mip/branching.py
========================
Branching variable selection strategies (§6.8).
Supports most-fractional, pseudocost, and reliability branching.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional
import numpy as np

from nirbhar.io.model import Model


@dataclass
class PseudocostData:
    up_cost: np.ndarray    # shape (n,) float64
    down_cost: np.ndarray  # shape (n,) float64
    up_count: np.ndarray   # shape (n,) int32
    down_count: np.ndarray # shape (n,) int32


def init_pseudocosts(ncols: int) -> PseudocostData:
    return PseudocostData(
        up_cost=np.ones(ncols, dtype=np.float64),
        down_cost=np.ones(ncols, dtype=np.float64),
        up_count=np.zeros(ncols, dtype=np.int32),
        down_count=np.zeros(ncols, dtype=np.int32),
    )


def update_pseudocosts(
    pseudocosts: PseudocostData,
    var_idx: int,
    direction: str,  # 'up' or 'down'
    delta_obj: float,
    fractional_dist: float,
) -> None:
    if fractional_dist < 1e-6:
        return
    unit_gain = max(0.0, delta_obj) / fractional_dist
    if direction == "up":
        c = pseudocosts.up_count[var_idx]
        pseudocosts.up_count[var_idx] += 1
        pseudocosts.up_cost[var_idx] = (pseudocosts.up_cost[var_idx] * c + unit_gain) / (c + 1)
    else:
        c = pseudocosts.down_count[var_idx]
        pseudocosts.down_count[var_idx] += 1
        pseudocosts.down_cost[var_idx] = (pseudocosts.down_cost[var_idx] * c + unit_gain) / (c + 1)


@dataclass
class BranchDecision:
    var_index: int
    var_name: str
    fractional_value: float
    branch_point: int


def select_branching_variable(
    model: Model,
    x: np.ndarray,
    strategy: str = "most_fractional",
    pseudocosts: Optional[PseudocostData] = None,
) -> Optional[BranchDecision]:
    """
    Select the integer variable to branch on.
    Returns None if all integer variables are integer feasible.
    """
    integrality = model.integrality
    if integrality is None:
        return None

    n = model.ncols
    best_idx = -1
    best_score = -math.inf
    best_val = 0.0

    for j in range(n):
        if integrality[j] == 0:
            continue

        val = float(x[j])
        floor_val = math.floor(val)
        frac = val - floor_val

        if frac < 1e-4 or frac > 1.0 - 1e-4:
            continue

        score = 0.0
        if strategy == "most_fractional":
            score = 0.5 - abs(frac - 0.5)
        elif strategy == "pseudocost" and pseudocosts is not None:
            up_score = (1.0 - frac) * float(pseudocosts.up_cost[j])
            down_score = frac * float(pseudocosts.down_cost[j])
            score = max(1e-4, down_score) * max(1e-4, up_score)
        elif strategy == "reliability" and pseudocosts is not None:
            count = min(int(pseudocosts.up_count[j]), int(pseudocosts.down_count[j]))
            if count < 4:
                score = 100.0 + (0.5 - abs(frac - 0.5))
            else:
                up_score = (1.0 - frac) * float(pseudocosts.up_cost[j])
                down_score = frac * float(pseudocosts.down_cost[j])
                score = max(1e-4, down_score) * max(1e-4, up_score)
        else:
            score = 0.5 - abs(frac - 0.5)

        if score > best_score:
            best_score = score
            best_idx = j
            best_val = val

    if best_idx == -1:
        return None

    var_name = model.col_names[best_idx] if best_idx < len(model.col_names) else f"x{best_idx + 1}"
    return BranchDecision(
        var_index=best_idx,
        var_name=var_name,
        fractional_value=best_val,
        branch_point=math.floor(best_val),
    )
