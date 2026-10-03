"""
nirbhar/ipm/mehrotra.py
========================
Phase 2 M5: Mehrotra Predictor-Corrector Interior Point Method for LP.

Solves the standard form LP:
    min  c^T x
    s.t. A x = b
         x >= 0

via the Mehrotra predictor-corrector algorithm using normal equations.

Algorithm
---------
Each iteration:
  1. Predictor: solve KKT system with sigma=0 (affine direction)
  2. Compute adaptive centering: sigma = (mu_aff / mu)^3
  3. Corrector: solve with sigma * mu (combined direction)
  4. Step length: Fraction-to-boundary with gamma=0.9995

Normal equations: (A D^2 A^T) Δy = rhs  where D = diag(x/s)
Solve via dense Cholesky (Phase 2; sparse in Phase 3).

Returns LPResult with status OPTIMAL | MAX_ITER | NUMERICAL.

Sovereignty: no scipy / cvxpy / highspy etc.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union

import numpy as np

from nirbhar.io.model import Model, INF
from nirbhar.lp.dual_simplex import LPResult, FarkasRay, UnboundedRay


@dataclass
class IPMOptions:
    max_iter: int = 200
    tol_feas: float = 1e-8      # primal/dual feasibility tolerance
    tol_gap: float = 1e-8       # relative duality gap tolerance
    gamma: float = 0.9995       # step-length safety factor
    min_step: float = 1e-14     # abort if step too small (near-singular)
    verbose: bool = False


def mehrotra_ipm(
    model: Model,
    opts: Optional[IPMOptions] = None,
) -> LPResult:
    """
    Solve LP with Mehrotra predictor-corrector IPM.

    The model is converted to equality standard form internally:
        min c^T x'
        s.t. A x' = b_eq,  x' >= 0

    with slacks added for inequality rows.

    Parameters
    ----------
    model : Model (LP only; integrality ignored)
    opts  : IPMOptions

    Returns
    -------
    LPResult
    """
    if opts is None:
        opts = IPMOptions()

    m_orig, n_orig = model.nrows, model.ncols

    # ── Build equality standard form ──────────────────────────────────────────
    c_eq, A_eq, b_eq, lo_shift, n_eq = _to_equality_form(model)
    m_eq = A_eq.shape[0]

    # ── Starting point (Mehrotra heuristic) ───────────────────────────────────
    x, s, y = _starting_point(A_eq, b_eq, c_eq, m_eq, n_eq)

    prev_gap = float("inf")

    for it in range(1, opts.max_iter + 1):
        # ── Residuals ─────────────────────────────────────────────────────────
        rp = b_eq - A_eq @ x           # primal residual
        rd = c_eq - A_eq.T @ y - s     # dual residual
        mu = float(x @ s) / n_eq       # complementarity measure

        # ── Convergence check ─────────────────────────────────────────────────
        rp_norm = np.linalg.norm(rp) / (1.0 + np.linalg.norm(b_eq))
        rd_norm = np.linalg.norm(rd) / (1.0 + np.linalg.norm(c_eq))
        obj_p = float(c_eq @ x)
        obj_d = float(b_eq @ y)
        gap_rel = abs(obj_p - obj_d) / (1.0 + abs(obj_d))

        if opts.verbose:
            print(f"  IPM it={it:3d}  mu={mu:.3e}  rp={rp_norm:.2e}  "
                  f"rd={rd_norm:.2e}  gap={gap_rel:.2e}")

        if rp_norm < opts.tol_feas and rd_norm < opts.tol_feas and gap_rel < opts.tol_gap:
            break

        if abs(gap_rel - prev_gap) < 1e-14 * prev_gap and it > 20:
            break  # stalled

        prev_gap = gap_rel

        # ── Normal equations matrix: M = A D^2 A^T ───────────────────────────
        D2 = x / s          # D^2 = X S^{-1}
        AD = A_eq * D2[None, :]       # A @ diag(D^2)
        M = AD @ A_eq.T               # (m_eq, m_eq)

        # ── Cholesky factorization (with regularization) ───────────────────────
        try:
            L = _cholesky(M)
        except np.linalg.LinAlgError:
            # Add small regularization
            reg = 1e-8 * np.trace(M) / m_eq
            try:
                L = _cholesky(M + reg * np.eye(m_eq))
            except np.linalg.LinAlgError:
                return LPResult(
                    status="NUMERICAL", x=np.zeros(n_orig), y=np.zeros(m_orig),
                    z_primal=float("inf"), z_dual=float("-inf"), gap=float("inf"),
                    iters=it, msg="IPM: normal equations singular",
                )

        # ── Predictor direction (sigma=0, mu_p=0) ────────────────────────────
        rhs_aff = rp + A_eq @ (D2 * rd + x)
        Δy_aff = _chol_solve(L, rhs_aff)
        Δs_aff = rd - A_eq.T @ Δy_aff
        Δx_aff = -D2 * Δs_aff - x

        # Step lengths for affine direction
        alpha_x_aff = _max_step(x, Δx_aff, 1.0)
        alpha_s_aff = _max_step(s, Δs_aff, 1.0)
        alpha_aff = min(alpha_x_aff, alpha_s_aff)

        mu_aff = float((x + alpha_aff * Δx_aff) @ (s + alpha_aff * Δs_aff)) / n_eq
        sigma = min((mu_aff / max(mu, 1e-300)) ** 3, 1.0)

        # ── Corrector direction (with centering & Mehrotra cross term) ────────
        cross = Δx_aff * Δs_aff
        inner = D2 * rd + x + (cross - sigma * mu) / s
        rhs_ctr = rp + A_eq @ inner

        Δy = _chol_solve(L, rhs_ctr)
        Δs = rd - A_eq.T @ Δy
        Δx = -D2 * Δs - x + (sigma * mu - cross) / s

        # ── Step lengths ──────────────────────────────────────────────────────
        alpha_x = _max_step(x, Δx, opts.gamma)
        alpha_s = _max_step(s, Δs, opts.gamma)

        if min(alpha_x, alpha_s) < opts.min_step:
            return LPResult(
                status="NUMERICAL", x=np.zeros(n_orig), y=np.zeros(m_orig),
                z_primal=float("inf"), z_dual=float("-inf"), gap=float("inf"),
                iters=it, msg="IPM: step length too small",
            )

        # ── Update iterates ───────────────────────────────────────────────────
        x = x + alpha_x * Δx
        s = s + alpha_s * Δs
        y = y + alpha_s * Δy

        # Safeguard: keep x, s > 0
        x = np.maximum(x, 1e-300)
        s = np.maximum(s, 1e-300)

    # ── Extract solution in original space ────────────────────────────────────
    x_orig = _extract_original(x, lo_shift, n_orig, n_eq)
    y_orig = y[:m_orig]

    z_p = float(model.c @ x_orig) + model.obj_const
    z_d = float(b_eq @ y) + float(model.c @ lo_shift) + model.obj_const
    gap = abs(z_p - z_d) / (1.0 + abs(z_d))

    status = "OPTIMAL" if (rp_norm < opts.tol_feas * 10
                           and rd_norm < opts.tol_feas * 10
                           and gap < opts.tol_gap * 10) else "MAX_ITER"

    return LPResult(
        status=status,
        x=x_orig,
        y=y_orig,
        z_primal=z_p,
        z_dual=z_d,
        gap=gap,
        iters=it,
        msg=f"IPM: {status} in {it} iterations",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_equality_form(model: Model):
    """Convert to equality standard form with row and column slacks, lower-bound shifted."""
    m, n = model.nrows, model.ncols
    A_csr = model.A_csr

    A = np.zeros((m, n), dtype=np.float64)
    for i in range(m):
        s, e = A_csr.indptr[i], A_csr.indptr[i + 1]
        for k in range(s, e):
            A[i, A_csr.indices[k]] = A_csr.data[k]

    ub_cols = [j for j in range(n) if model.col_hi[j] < INF * 0.9]
    n_ub = len(ub_cols)

    total_rows = m + n_ub
    total_cols = n + m + n_ub

    A_eq = np.zeros((total_rows, total_cols), dtype=np.float64)
    A_eq[:m, :n] = A
    c_eq = np.zeros(total_cols, dtype=np.float64)
    c_eq[:n] = model.c
    b_eq = np.zeros(total_rows, dtype=np.float64)

    for i in range(m):
        lo_r, hi_r = model.row_lo[i], model.row_hi[i]
        finite_lo = lo_r > -INF * 0.9
        finite_hi = hi_r < INF * 0.9

        if finite_lo and finite_hi and abs(hi_r - lo_r) < 1e-12:
            b_eq[i] = lo_r  # equality
        elif finite_hi:
            A_eq[i, n + i] = 1.0; b_eq[i] = hi_r   # L row
        elif finite_lo:
            A_eq[i, n + i] = -1.0; b_eq[i] = lo_r  # G row
        else:
            b_eq[i] = 0.0  # free

    # Add upper bound constraints: x_j + s_ub = col_hi[j]
    for idx, j in enumerate(ub_cols):
        r = m + idx
        c_slack = n + m + idx
        A_eq[r, j] = 1.0
        A_eq[r, c_slack] = 1.0
        b_eq[r] = model.col_hi[j]

    # Lower-bound shift
    col_lo = np.clip(model.col_lo, -INF * 0.9, INF * 0.9)
    for j in range(n):
        lj = col_lo[j]
        if abs(lj) > 1e-300:
            b_eq -= A_eq[:, j] * lj

    lo_shift = col_lo.copy()
    return c_eq, A_eq, b_eq, lo_shift, total_cols


def _starting_point(
    A: np.ndarray, b: np.ndarray, c: np.ndarray, m: int, n: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Mehrotra's starting-point heuristic."""
    # Least-squares primal: x0 = A^T (A A^T)^{-1} b
    AAt = A @ A.T
    try:
        rhs_b = np.linalg.solve(AAt + 1e-8 * np.eye(m), b)
    except np.linalg.LinAlgError:
        rhs_b = np.zeros(m)
    x0 = A.T @ rhs_b

    # Least-squares dual: y0 = (A A^T)^{-1} A c, s0 = c - A^T y0
    try:
        rhs_c = np.linalg.solve(AAt + 1e-8 * np.eye(m), A @ c)
    except np.linalg.LinAlgError:
        rhs_c = np.zeros(m)
    y0 = rhs_c
    s0 = c - A.T @ y0

    # Shift to strictly positive
    dx = max(0.0, -1.5 * x0.min()) + 1.0
    ds = max(0.0, -1.5 * s0.min()) + 1.0
    x0 += dx
    s0 += ds

    # Additional centering shift (Mehrotra §2.3)
    mu0 = float(x0 @ s0) / n
    dx2 = 0.5 * mu0 / (s0.sum() / n) if s0.sum() > 0 else 0.0
    ds2 = 0.5 * mu0 / (x0.sum() / n) if x0.sum() > 0 else 0.0
    x0 += dx2
    s0 += ds2

    return x0, s0, y0


def _cholesky(M: np.ndarray) -> np.ndarray:
    """Dense Cholesky: returns lower-triangular L such that M = L L^T."""
    return np.linalg.cholesky(M)


def _chol_solve(L: np.ndarray, rhs: np.ndarray) -> np.ndarray:
    """Solve M x = rhs given L (lower Cholesky factor)."""
    # Forward: L y = rhs
    y = np.linalg.solve(L, rhs)
    # Backward: L^T x = y
    return np.linalg.solve(L.T, y)


def _max_step(v: np.ndarray, dv: np.ndarray, gamma: float) -> float:
    """Largest alpha in (0,1] such that v + alpha*dv >= (1-gamma)*v."""
    neg = dv < 0
    if not np.any(neg):
        return 1.0
    ratios = -gamma * v[neg] / dv[neg]
    return float(min(1.0, ratios.min()))


def _extract_original(
    x_eq: np.ndarray,
    lo_shift: np.ndarray,
    n_orig: int,
    n_eq: int,
) -> np.ndarray:
    """Undo lower-bound shift and extract original n variables."""
    x_orig = x_eq[:n_orig] + lo_shift
    return x_orig
