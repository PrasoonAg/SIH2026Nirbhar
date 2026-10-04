"""
nirbhar/hpr/__init__.py
=======================
Halpern-Peaceman-Rachford (HPR) GPU-native first-order optimization module.
"""

from nirbhar.hpr.hpr_solver import (
    hpr_solve,
    hpr_batch_solve,
    HPROptions,
    BatchScenario,
    BatchResult,
)

__all__ = [
    "hpr_solve",
    "hpr_batch_solve",
    "HPROptions",
    "BatchScenario",
    "BatchResult",
]
