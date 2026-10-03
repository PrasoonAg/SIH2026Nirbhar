"""
nirbhar/cuts/cmir.py
====================
Complemented Mixed-Integer Rounding (c-MIR) Cuts (§6.9).
"""

from __future__ import annotations
import math
import numpy as np
from nirbhar.io.model import Model, INF
from nirbhar.cuts.types import CutRecord


def generate_cmir_cuts(
    model: Model,
    x_lp: np.ndarray,
    min_fractionality: float = 0.05,
    max_cuts: int = 6,
    scales: list[float] | None = None,
) -> list[CutRecord]:
    """
    Generate c-MIR cuts from bounded constraints with scaling exploration.
    """
    if scales is None:
        scales = [1.0, 0.5, 2.0, 0.25]

    cuts: list[CutRecord] = []
    n = model.ncols
    m = model.nrows
    integrality = model.integrality

    if integrality is None or not np.any(integrality):
        return cuts

    A_csr = model.A_csr

    for i in range(m):
        row_hi = float(model.row_hi[i])
        if row_hi >= INF * 0.9:
            continue

        s, e = A_csr.indptr[i], A_csr.indptr[i + 1]
        cols = A_csr.indices[s:e]
        data = A_csr.data[s:e]

        # Check if row contains integer variables
        if not np.any(integrality[cols] != 0):
            continue

        for delta in scales:
            b_scaled = row_hi * delta
            f = b_scaled - math.floor(b_scaled)
            if f < 0.05 or f > 0.95:
                continue

            coeffs = np.zeros(n, dtype=np.float64)

            for idx, j in enumerate(cols):
                a_scaled = float(data[idx]) * delta
                is_int = (integrality[j] != 0)

                if is_int:
                    fa = a_scaled - math.floor(a_scaled)
                    coeffs[j] = math.floor(a_scaled) + ((fa - f) / (1.0 - f) if fa > f else 0.0)
                else:
                    coeffs[j] = (a_scaled / (1.0 - f)) if a_scaled < 0.0 else 0.0

            # Form: coeffs @ x >= rhs
            coeffs = -coeffs
            rhs = -math.floor(b_scaled)

            lp_val = float(coeffs @ x_lp)
            if lp_val < rhs - 1e-5:
                cuts.append(CutRecord(
                    kind="CMIR",
                    coeffs=coeffs,
                    rhs=rhs,
                    lp_value=lp_val,
                    source_row=i,
                ))
                break  # one scale per row

        if len(cuts) >= max_cuts:
            break

    return cuts
