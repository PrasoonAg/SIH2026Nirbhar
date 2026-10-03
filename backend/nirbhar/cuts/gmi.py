"""
nirbhar/cuts/gmi.py
===================
Gomory Mixed-Integer (GMI) Cuts (§6.9).
"""

from __future__ import annotations
import math
import numpy as np
from nirbhar.io.model import Model, INF
from nirbhar.cuts.types import CutRecord


def generate_gmi_cuts(
    model: Model,
    x_lp: np.ndarray,
    min_fractionality: float = 0.05,
    max_cuts: int = 10,
) -> list[CutRecord]:
    """
    Generate Gomory Mixed-Integer cuts from fractional variables and basis rows.
    """
    cuts: list[CutRecord] = []
    n = model.ncols
    m = model.nrows
    integrality = model.integrality

    if integrality is None or not np.any(integrality):
        return cuts

    A_csr = model.A_csr

    for j in range(n):
        if integrality[j] == 0:
            continue

        val = float(x_lp[j])
        floor_val = math.floor(val)
        frac = val - floor_val

        if frac < min_fractionality or frac > (1.0 - min_fractionality):
            continue

        # Find rows containing j
        for i in range(m):
            s, e = A_csr.indptr[i], A_csr.indptr[i + 1]
            cols = A_csr.indices[s:e]
            data = A_csr.data[s:e]

            j_matches = np.where(cols == j)[0]
            if len(j_matches) == 0:
                continue

            a_ij = float(data[j_matches[0]])
            if abs(a_ij) < 1e-4:
                continue

            b = float(model.row_hi[i]) if model.row_hi[i] < INF * 0.9 else float(model.row_lo[i])
            if not math.isfinite(b):
                continue

            rhs_div = b / abs(a_ij)
            f0 = rhs_div - math.floor(rhs_div)
            if f0 < 0.02 or f0 > 0.98:
                continue

            cut_rhs = math.floor(rhs_div)
            coeffs = np.zeros(n, dtype=np.float64)

            for col_idx, k in enumerate(cols):
                a_k = float(data[col_idx]) / abs(a_ij)
                is_int = (integrality[k] != 0)

                if is_int:
                    fa = a_k - math.floor(a_k)
                    coeffs[k] = math.floor(a_k) + ((fa - f0) / (1.0 - f0) if fa > f0 else 0.0)
                else:
                    coeffs[k] = (a_k / (1.0 - f0)) if a_k < 0.0 else 0.0

            # Form: coeffs @ x >= cut_rhs
            coeffs = -coeffs
            cut_rhs = -cut_rhs

            lp_val = float(coeffs @ x_lp)
            if lp_val < cut_rhs - 1e-6:
                cuts.append(CutRecord(
                    kind="GMI",
                    coeffs=coeffs,
                    rhs=cut_rhs,
                    lp_value=lp_val,
                    source_row=i,
                ))
                break

        if len(cuts) >= max_cuts:
            break

    return cuts
