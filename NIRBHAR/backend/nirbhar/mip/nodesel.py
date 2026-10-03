"""
nirbhar/mip/nodesel.py
======================
Branch-and-Bound node selection strategies (§6.8).
Supports:
  - best_bound: lowest lower bound (breadth/optimality focused)
  - depth_first: deepest node first (diving/incumbent focused)
  - best_estimate: estimated integer objective via degradation
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class BNode:
    id: int
    parent_id: Optional[int]
    depth: int
    lower_bound: float
    lp_objective: float
    col_lower: np.ndarray
    col_upper: np.ndarray
    status: str = "open"  # 'open' | 'pruned' | 'integer' | 'infeasible'
    branch_var_name: Optional[str] = None
    branch_dir: Optional[str] = None  # 'left' (<=) or 'right' (>=)
    branch_bound: Optional[float] = None
    x: Optional[np.ndarray] = None


def select_next_node(
    open_nodes: list[BNode],
    strategy: str = "best_bound",
) -> Optional[tuple[BNode, int]]:
    """
    Select the next node to explore from the open nodes pool.
    Returns (node, index_in_open_nodes) or None if pool is empty.
    """
    if not open_nodes:
        return None

    best_idx = 0

    if strategy == "best_bound":
        # Min lower bound
        min_lb = open_nodes[0].lower_bound
        for i in range(1, len(open_nodes)):
            if open_nodes[i].lower_bound < min_lb:
                min_lb = open_nodes[i].lower_bound
                best_idx = i

    elif strategy == "depth_first":
        # Max depth, tie-break on min lower bound
        max_depth = open_nodes[0].depth
        for i in range(1, len(open_nodes)):
            node = open_nodes[i]
            if node.depth > max_depth or (
                node.depth == max_depth and node.lower_bound < open_nodes[best_idx].lower_bound
            ):
                max_depth = node.depth
                best_idx = i

    elif strategy == "best_estimate":
        best_score = open_nodes[0].lower_bound + 0.05 * open_nodes[0].depth
        for i in range(1, len(open_nodes)):
            score = open_nodes[i].lower_bound + 0.05 * open_nodes[i].depth
            if score < best_score:
                best_score = score
                best_idx = i

    else:
        # Default to best bound
        min_lb = open_nodes[0].lower_bound
        for i in range(1, len(open_nodes)):
            if open_nodes[i].lower_bound < min_lb:
                min_lb = open_nodes[i].lower_bound
                best_idx = i

    return open_nodes[best_idx], best_idx
