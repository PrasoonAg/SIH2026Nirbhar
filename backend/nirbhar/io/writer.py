"""
nirbhar/io/writer.py
====================
MPS/QPS writer for round-trip testing and model export.
Writes a Model back to a standard (free-format) MPS string.
"""

from __future__ import annotations
from nirbhar.io.model import Model, INF
import numpy as np


def model_to_mps(model: Model) -> str:
    """Write a Model to MPS string (free-format, minimisation)."""
    lines: list[str] = []

    # NAME
    lines.append(f"NAME          {model.obj_name or 'MODEL'}")

    # ROWS
    lines.append("ROWS")
    lines.append(f" N  {model.obj_name or 'obj'}")
    for i, name in enumerate(model.row_names):
        lo, hi = model.row_lo[i], model.row_hi[i]
        if lo == hi:
            rtype = "E"
        elif lo <= -INF * 0.9:
            rtype = "L"
        elif hi >= INF * 0.9:
            rtype = "G"
        else:
            rtype = "G"   # will add RANGES later for double-bounded
        lines.append(f" {rtype}  {name}")

    # COLUMNS (with integer markers)
    lines.append("COLUMNS")
    in_int = False

    def _toggle_int(want: bool) -> None:
        nonlocal in_int
        if want and not in_int:
            lines.append("    MARKER                'MARKER'                 'INTORG'")
            in_int = True
        elif not want and in_int:
            lines.append("    MARKER                'MARKER'                 'INTEND'")
            in_int = False

    for j, cname in enumerate(model.col_names):
        is_int = model.integrality[j] > 0
        _toggle_int(is_int)

        obj_val = model.c[j]
        if model.sense == "max":
            obj_val = -obj_val  # write original sense

        entries: list[tuple[str, float]] = []
        if obj_val != 0.0:
            entries.append((model.obj_name or "obj", obj_val))

        for i in range(model.nrows):
            start, end = model.A_csr.indptr[i], model.A_csr.indptr[i + 1]
            for k in range(start, end):
                if model.A_csr.indices[k] == j:
                    entries.append((model.row_names[i], model.A_csr.data[k]))

        if not entries:
            entries.append((model.obj_name or "obj", 0.0))

        # write in pairs
        for idx in range(0, len(entries), 2):
            row1, val1 = entries[idx]
            if idx + 1 < len(entries):
                row2, val2 = entries[idx + 1]
                lines.append(f"    {cname:<10}  {row1:<10}  {val1:>14g}   {row2:<10}  {val2:>14g}")
            else:
                lines.append(f"    {cname:<10}  {row1:<10}  {val1:>14g}")

    _toggle_int(False)

    # RHS
    lines.append("RHS")
    for i, rname in enumerate(model.row_names):
        lo, hi = model.row_lo[i], model.row_hi[i]
        rhs = lo if lo > -INF * 0.9 else hi if hi < INF * 0.9 else 0.0
        lines.append(f"    RHS         {rname:<10}  {rhs:>14g}")

    if model.obj_const != 0.0:
        obj_rhs = -model.obj_const if model.sense == "min" else model.obj_const
        lines.append(f"    RHS         {model.obj_name or 'obj':<10}  {obj_rhs:>14g}")

    # BOUNDS
    lines.append("BOUNDS")
    for j, cname in enumerate(model.col_names):
        lo, hi = model.col_lo[j], model.col_hi[j]
        integ = model.integrality[j]
        if integ == 2:
            lines.append(f" BV BND       {cname}")
        elif lo == hi:
            lines.append(f" FX BND       {cname:<10}  {lo:>14g}")
        elif lo <= -INF * 0.9 and hi >= INF * 0.9:
            lines.append(f" FR BND       {cname}")
        elif lo <= -INF * 0.9:
            lines.append(f" MI BND       {cname}")
            if hi < INF * 0.9:
                btype = "UI" if integ >= 1 else "UP"
                lines.append(f" {btype} BND       {cname:<10}  {hi:>14g}")
        else:
            if lo != 0.0:
                btype = "LI" if integ == 1 else "LO"
                lines.append(f" {btype} BND       {cname:<10}  {lo:>14g}")
            if hi < INF * 0.9:
                btype = "UI" if integ == 1 else "UP"
                lines.append(f" {btype} BND       {cname:<10}  {hi:>14g}")

    # QUADOBJ (if present)
    if model.Q_upper:
        lines.append("QUADOBJ")
        for (i, j), v in sorted(model.Q_upper.items()):
            ci, cj = model.col_names[i], model.col_names[j]
            val = v if i == j else v * 2.0   # restore full value
            lines.append(f"    {ci:<10}  {cj:<10}  {val:>14g}")

    lines.append("ENDATA")
    return "\n".join(lines) + "\n"
