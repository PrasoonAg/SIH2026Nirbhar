"""
nirbhar/io/qps.py
=================
QPS format extensions — delegates to mps.py for the LP part and adds
QUADOBJ/QMATRIX section parsing.  Since mps.py already handles QUADOBJ
inline, this module exists as a thin convenience wrapper and for future
extension of the QPS dialect.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional

from nirbhar.io.mps import parse_mps
from nirbhar.io.model import Model


def parse_qps(
    path: Optional[str | Path] = None,
    *,
    text: Optional[str] = None,
) -> Model:
    """
    Parse a QPS (MPS + QUADOBJ) file.
    Identical to parse_mps; the QUADOBJ section is handled by the same parser.
    """
    return parse_mps(path, text=text)
