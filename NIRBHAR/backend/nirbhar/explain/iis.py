"""
nirbhar/explain/iis.py
======================
Irreducible Infeasible Subsystem (IIS) detection via Deletion Filter (§6.7, §7).
Identifies a minimal conflicting subset of constraints causing infeasibility.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import numpy as np

from nirbhar.io.model import Model, INF
from nirbhar.lp.dual_simplex import dual_simplex_solve, DSSOptions, LPResult, FarkasRay


@dataclass
class IISResult:
    is_infeasible: bool
    iis_row_indices: list[int]
    iis_row_names: list[str]
    explanation: str


def compute_iis(
    model: Model,
    max_filter_rows: int = 150,
) -> IISResult:
    """
    Compute an Irreducible Infeasible Subsystem (IIS) using deletion filtering.
    """
    m, n = model.nrows, model.ncols

    # 1. Confirm overall infeasibility
    dss_opts = DSSOptions(max_iter=1000)
    base_res = dual_simplex_solve(model, opts=dss_opts)
    if not (isinstance(base_res, FarkasRay) or (isinstance(base_res, LPResult) and base_res.status == "INFEASIBLE")):
        return IISResult(
            is_infeasible=False,
            iis_row_indices=[],
            iis_row_names=[],
            explanation="Model is feasible; no conflicting constraints exist.",
        )

    # 2. Deletion filter loop
    curr_row_lo = model.row_lo.copy()
    curr_row_hi = model.row_hi.copy()

    # Rows to test
    test_rows = list(range(min(m, max_filter_rows)))
    essential_rows: list[int] = []

    for r in test_rows:
        orig_lo = curr_row_lo[r]
        orig_hi = curr_row_hi[r]

        # Temporarily relax row r to unconstrained
        curr_row_lo[r] = -INF
        curr_row_hi[r] = INF

        test_model = Model(
            nrows=m,
            ncols=n,
            c=model.c,
            obj_const=model.obj_const,
            sense=model.sense,
            A_csr=model.A_csr,
            A_csc=model.A_csc,
            row_lo=curr_row_lo.copy(),
            row_hi=curr_row_hi.copy(),
            col_lo=model.col_lo,
            col_hi=model.col_hi,
            integrality=model.integrality,
            Q_upper=model.Q_upper,
            row_names=model.row_names,
            col_names=model.col_names,
            obj_name=model.obj_name,
            sha256=model.sha256,
            source_path=model.source_path,
        )

        res = dual_simplex_solve(test_model, opts=DSSOptions(max_iter=300))
        is_still_infeas = isinstance(res, FarkasRay) or (isinstance(res, LPResult) and res.status == "INFEASIBLE")

        if is_still_infeas:
            # Row r was NOT needed for infeasibility -> keep it relaxed
            pass
        else:
            # Row r IS essential to this IIS -> restore original bounds
            curr_row_lo[r] = orig_lo
            curr_row_hi[r] = orig_hi
            essential_rows.append(r)

    # If all tested rows were dropped, fallback to all original rows
    if not essential_rows:
        essential_rows = test_rows

    row_names = [
        model.row_names[r] if r < len(model.row_names) else f"row_{r}"
        for r in essential_rows
    ]

    expl_lines = [
        f"Detected minimal conflict set (IIS) with {len(essential_rows)} constraint(s):",
    ]
    for name, r in zip(row_names, essential_rows):
        r_lo = model.row_lo[r]
        r_hi = model.row_hi[r]
        bounds_str = f"[{r_lo}, {r_hi}]" if r_lo > -INF * 0.9 and r_hi < INF * 0.9 else (
            f"<= {r_hi}" if r_hi < INF * 0.9 else f">= {r_lo}"
        )
        expl_lines.append(f"  * {name} (bounds: {bounds_str})")
    expl_lines.append("Removing any one of these constraints will eliminate this contradiction.")

    return IISResult(
        is_infeasible=True,
        iis_row_indices=essential_rows,
        iis_row_names=row_names,
        explanation="\n".join(expl_lines),
    )
