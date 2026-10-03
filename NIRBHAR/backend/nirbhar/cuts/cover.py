"""
nirbhar/cuts/cover.py
=====================
Extended Knapsack Cover Cuts (§6.9).
"""

from __future__ import annotations
import numpy as np
from nirbhar.io.model import Model, INF
from nirbhar.cuts.types import CutRecord


def generate_cover_cuts(
    model: Model,
    x_lp: np.ndarray,
    max_cuts: int = 6,
) -> list[CutRecord]:
    """
    Generate knapsack cover cuts from binary knapsack constraints.
    """
    cuts: list[CutRecord] = []
    n = model.ncols
    m = model.nrows
    integrality = model.integrality

    if integrality is None or not np.any(integrality):
        return cuts

    A_csr = model.A_csr

    for i in range(m):
        row_hi = float(model.row_hi[i])
        if row_hi >= INF * 0.9 or row_hi <= 0.0:
            continue

        s, e = A_csr.indptr[i], A_csr.indptr[i + 1]
        cols = A_csr.indices[s:e]
        data = A_csr.data[s:e]

        bin_cols: list[int] = []
        bin_weights: list[float] = []
        all_pos_bin = True

        for idx, j in enumerate(cols):
            val = float(data[idx])
            is_bin = (
                integrality[j] != 0
                and abs(model.col_lo[j]) < 1e-8
                and abs(model.col_hi[j] - 1.0) < 1e-8
            )
            if is_bin and val > 0.0:
                bin_cols.append(j)
                bin_weights.append(val)
            elif val < 0.0:
                all_pos_bin = False
                break

        if not all_pos_bin or len(bin_cols) < 2:
            continue

        # Sort candidate binary columns by decreasing LP value
        order = sorted(range(len(bin_cols)), key=lambda k: -x_lp[bin_cols[k]])

        sum_weight = 0.0
        cover_cols: list[int] = []

        for idx in order:
            cover_cols.append(bin_cols[idx])
            sum_weight += bin_weights[idx]
            if sum_weight > row_hi:
                break

        if sum_weight > row_hi and len(cover_cols) >= 2:
            lp_sum = sum(x_lp[c] for c in cover_cols)
            max_allowed = len(cover_cols) - 1

            if lp_sum > max_allowed + 1e-4:
                coeffs = np.zeros(n, dtype=np.float64)
                for c in cover_cols:
                    coeffs[c] = -1.0
                rhs = -float(max_allowed)

                cuts.append(CutRecord(
                    kind="COVER",
                    coeffs=coeffs,
                    rhs=rhs,
                    lp_value=-lp_sum,
                    source_row=i,
                ))

        if len(cuts) >= max_cuts:
            break

    return cuts
