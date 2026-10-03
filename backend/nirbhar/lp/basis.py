"""
nirbhar/lp/basis.py
====================
LP basis management.

A basis B is a set of m column indices from [A | I_slacks].
This module manages:
  - Constructing the basis matrix B from model data
  - Tracking basic/nonbasic variable status
  - Triggering refactorization when needed (eta-file grows too large or
    condition number estimate exceeds threshold)

Phase 1: dense factorization (LUFactor).
Phase 2: sparse Markowitz LU.

Status conventions (following HiGHS/GLPK numbering):
  NONBASIC_AT_LOWER = -1
  NONBASIC_AT_UPPER = -2
  NONBASIC_FREE     = -3
  BASIC             =  index >= 0 (index into basic variable list)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from nirbhar.io.model import Model, CSRMatrix, INF
from nirbhar.linalg.lu_markowitz import LUFactor, SingularBasisError
from nirbhar.linalg.refine import iterative_refine


NONBASIC_AT_LOWER: int = -1
NONBASIC_AT_UPPER: int = -2
NONBASIC_FREE: int = -3

# Refactorize when eta count exceeds this or cond estimate > COND_THRESHOLD
MAX_ETA_UPDATES: int = 50
COND_THRESHOLD: float = 1e10


@dataclass
class Basis:
    """
    LP basis state for a model with m constraints and n structural variables.

    Columns in the extended system: [A | I_slacks], total = n + m columns.
    Basic indices are drawn from {0, ..., n+m-1}.
    """
    m: int                              # number of constraint rows
    n: int                              # number of structural variables
    # basic_vars[i] = column index in [A|I] of the variable in row i's basis slot
    basic_vars: np.ndarray              # shape (m,) int32
    # status[j] for j in 0..n+m-1: NONBASIC_AT_LOWER/UPPER/FREE or BASIC (not used here)
    vstat: np.ndarray                   # shape (n+m,) int8
    lu: Optional[LUFactor] = field(default=None, repr=False)
    B_dense: Optional[np.ndarray] = field(default=None, repr=False)
    eta_count: int = 0
    _is_fresh: bool = False

    # ── Construction ────────────────────────────────────────────────────────

    @classmethod
    def slack_basis(cls, model: Model) -> "Basis":
        """
        Initial all-slack basis: basic variable i is slack s_i (column n+i).
        Only valid for models with finite row_hi (L/E constraints after preprocessing).
        """
        m, n = model.nrows, model.ncols
        basic_vars = np.arange(n, n + m, dtype=np.int32)
        vstat = np.full(n + m, NONBASIC_AT_LOWER, dtype=np.int8)
        vstat[n:] = 0   # slacks are basic (re-using 0 for BASIC in vstat)
        b = cls(m=m, n=n, basic_vars=basic_vars, vstat=vstat)
        b._build_dense(model)
        b._refactor()
        return b

    # ── Dense basis matrix ───────────────────────────────────────────────────

    def _build_dense(self, model: Model) -> None:
        """Extract columns basic_vars from [A | I] as a dense (m x m) matrix."""
        m, n = self.m, self.n
        B = np.zeros((m, m), dtype=np.float64)
        A_csc = model.A_csc

        for slot, col in enumerate(self.basic_vars):
            if col < n:
                # Structural variable: copy column from A_csc
                s, e = A_csc.indptr[col], A_csc.indptr[col + 1]
                for k in range(s, e):
                    B[A_csc.indices[k], slot] = A_csc.data[k]
            else:
                # Slack variable for row (col - n)
                B[col - n, slot] = 1.0

        self.B_dense = B

    def _refactor(self) -> None:
        """LU-factorize the current dense basis matrix."""
        assert self.B_dense is not None
        try:
            self.lu = LUFactor.factor(self.B_dense)
            self.eta_count = 0
            self._is_fresh = True
        except SingularBasisError:
            # Attempt perturbation: add small identity
            perturbed = self.B_dense + np.eye(self.m) * 1e-8
            self.lu = LUFactor.factor(perturbed)
            self.eta_count = 0
            self._is_fresh = False

    # ── Solves ───────────────────────────────────────────────────────────────

    def btran(self, rhs: np.ndarray) -> np.ndarray:
        """
        Compute y = B^{-T} rhs  (used in pricing: y = c_B @ B^{-1}).
        """
        assert self.lu is not None
        return self.lu.solve(rhs, transpose=True)

    def ftran(self, rhs: np.ndarray) -> np.ndarray:
        """
        Compute x = B^{-1} rhs  (used in ratio test and update).
        """
        assert self.lu is not None
        return self.lu.solve(rhs, transpose=False)

    def ftran_refine(self, model: Model, rhs: np.ndarray) -> np.ndarray:
        """ftran with iterative refinement (used for high-accuracy x_B computation)."""
        assert self.lu is not None and self.B_dense is not None
        x0 = self.lu.solve(rhs)
        return iterative_refine(self.lu, self.B_dense, rhs, x0, steps=2)

    # ── Update (entering/leaving) ────────────────────────────────────────────

    def update(
        self,
        model: Model,
        entering: int,
        leaving_slot: int,
    ) -> None:
        """
        Pivot entering column into basis at slot leaving_slot.
        Triggers refactorization when eta count exceeds MAX_ETA_UPDATES
        or condition estimate is large.
        """
        self.basic_vars[leaving_slot] = entering
        self.eta_count += 1

        # Decide whether to refactorize
        needs_refactor = (
            self.eta_count >= MAX_ETA_UPDATES
            or (self.lu is not None
                and self.lu.condition_estimate() > COND_THRESHOLD)
        )

        if needs_refactor:
            self._build_dense(model)
            self._refactor()
        else:
            # Lazy: rebuild only when ratio test is requested next time
            # (Phase 1: always refactor every update for correctness)
            self._build_dense(model)
            self._refactor()

    # ── Feasibility check ────────────────────────────────────────────────────

    def basic_solution(self, model: Model, rhs: np.ndarray) -> np.ndarray:
        """
        Compute x_B = B^{-1} rhs with refinement.
        rhs is typically the RHS of the constraint system (b - A_N x_N).
        """
        return self.ftran_refine(model, rhs)

    def is_primal_feasible(
        self,
        x_B: np.ndarray,
        tol: float = 1e-8,
    ) -> bool:
        """Check if basic solution satisfies basic variable bounds."""
        # In Phase 1, all slacks are basic; structural bounds applied at bounds
        return bool(np.all(x_B >= -tol))
