"""
nirbhar/cuts/types.py
=====================
Data structures for cutting planes in NIRBHAR (§6.9).
"""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass
class CutRecord:
    kind: str           # 'GMI' | 'CMIR' | 'COVER'
    coeffs: np.ndarray  # Dense array of coefficients, shape (n,)
    rhs: float          # Lower bound: coeffs @ x >= rhs
    lp_value: float     # coeffs @ x_lp (violation if lp_value < rhs)
    source_row: int = -1
