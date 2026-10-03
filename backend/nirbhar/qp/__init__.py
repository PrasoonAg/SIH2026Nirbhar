"""
nirbhar/qp
==========
Convex Quadratic Optimization package for NIRBHAR (§6.10).
Supports:
  - Positive Semidefinite (PSD) verification & certification
  - Mehrotra Predictor-Corrector Interior Point solver for QP
  - Kelley's Outer-Approximation algorithm for Convex MIQP
"""

from nirbhar.qp.psd import check_psd
from nirbhar.qp.mehrotra_qp import qp_solve, QPOptions
from nirbhar.qp.outer_approx import outer_approximation_miqp, MIQPOptions, MIQPResult

__all__ = [
    "check_psd",
    "qp_solve",
    "QPOptions",
    "outer_approximation_miqp",
    "MIQPOptions",
    "MIQPResult",
]
