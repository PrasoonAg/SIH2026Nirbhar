"""
nirbhar_verify/mps_min.py
=========================
Minimal, self-contained MPS reader for the verifier.
CRITICAL: imports NOTHING from nirbhar/.
Only reads what the verifier needs: row/col names, constraint bounds,
variable bounds, and objective coefficients.  Does not build full CSR —
the verifier recomputes bounds from scratch.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

INF = 1e30


@dataclass
class MinModel:
    """Minimal model for verification purposes only."""
    nrows: int
    ncols: int
    c: np.ndarray          # (n,) objective, stored as minimisation
    A_dense: np.ndarray    # (m, n) constraint matrix (dense — small models only)
    row_lo: np.ndarray     # (m,) row lower bounds
    row_hi: np.ndarray     # (m,) row upper bounds
    col_lo: np.ndarray     # (n,) variable lower bounds
    col_hi: np.ndarray     # (n,) variable upper bounds
    integrality: np.ndarray  # (n,) int8
    sense: str             # 'min' or 'max'
    obj_const: float
    row_names: list[str]
    col_names: list[str]
    sha256: str
    source_path: Optional[str] = None


def _sha256(path: str | Path) -> str:
    data = Path(path).read_bytes()
    return hashlib.sha256(data).hexdigest()


def parse_mps_min(path: str | Path) -> MinModel:
    """Parse MPS file into MinModel for verification (no nirbhar imports)."""
    path = Path(path)
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()

    sense = "min"
    obj_name = ""
    row_names: list[str] = []
    row_types: list[str] = []
    col_names: list[str] = []
    col_index: dict[str, int] = {}
    row_index: dict[str, int] = {}

    entries: list[tuple[int, int, float]] = []   # (row_orig, col, val)
    obj_c: dict[int, float] = {}
    rhs_map: dict[int, float] = {}
    ranges_map: dict[int, float] = {}
    col_lo: dict[int, float] = {}
    col_hi: dict[int, float] = {}
    integ: dict[int, int] = {}
    _in_int = False
    section = ""

    SECTIONS = {"NAME","ROWS","COLUMNS","RHS","RANGES","BOUNDS",
                "OBJSENSE","QUADOBJ","QMATRIX","ENDATA"}

    def add_col(name: str) -> int:
        if name not in col_index:
            j = len(col_names)
            col_names.append(name)
            col_index[name] = j
            col_lo[j] = 0.0
            col_hi[j] = INF
            integ[j] = 0
        return col_index[name]

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line.strip() or line.startswith("*") or line.startswith("$"):
            continue
        tok = line.lstrip().split()[0].upper()
        if tok in SECTIONS:
            section = tok
            if section == "ENDATA":
                break
            continue

        parts = line.lstrip().split()
        if section == "OBJSENSE":
            sense = "max" if parts[0].upper() in ("MAX","MAXIMIZE","MAXIMISE") else "min"

        elif section == "ROWS":
            rt, rn = parts[0].upper(), parts[1]
            row_types.append(rt)
            row_index[rn] = len(row_names)
            row_names.append(rn)
            if rt == "N" and not obj_name:
                obj_name = rn

        elif section == "COLUMNS":
            if len(parts) >= 3 and parts[1].upper() == "MARKER":
                m = parts[2].strip("'").upper()
                _in_int = (m == "INTORG")
                continue
            cn = parts[0]
            j = add_col(cn)
            if _in_int and integ[j] == 0:
                integ[j] = 1
            idx = 1
            while idx + 1 < len(parts):
                rn, v = parts[idx], float(parts[idx+1])
                idx += 2
                ri = row_index[rn]
                if row_types[ri] == "N":
                    obj_c[j] = obj_c.get(j, 0.0) + v
                else:
                    entries.append((ri, j, v))

        elif section == "RHS":
            idx = 1
            while idx + 1 < len(parts):
                rn, v = parts[idx], float(parts[idx+1])
                idx += 2
                rhs_map[row_index[rn]] = v

        elif section == "RANGES":
            idx = 1
            while idx + 1 < len(parts):
                rn, v = parts[idx], float(parts[idx+1])
                idx += 2
                ranges_map[row_index[rn]] = v

        elif section == "BOUNDS":
            bt = parts[0].upper()
            cn = parts[2] if len(parts) > 2 and parts[1] not in col_index else parts[1]
            val_s = parts[3] if len(parts) > 3 and parts[1] not in col_index else (parts[2] if len(parts) > 2 else "0")
            j = col_index.get(cn)
            if j is None:
                continue
            try:
                v = float(val_s)
            except ValueError:
                v = 0.0
            if bt == "LO": col_lo[j] = v
            elif bt == "UP": col_hi[j] = v if v >= 0 or col_lo.get(j,0) != 0 else (0.0)
            elif bt == "FX": col_lo[j] = col_hi[j] = v
            elif bt == "FR": col_lo[j] = -INF; col_hi[j] = INF
            elif bt == "MI": col_lo[j] = -INF
            elif bt == "BV": col_lo[j]=0; col_hi[j]=1; integ[j]=2
            elif bt == "LI": col_lo[j]=v; integ[j]=max(integ.get(j,0),1)
            elif bt == "UI": col_hi[j]=v; integ[j]=max(integ.get(j,0),1)

    # Separate objective row from constraint rows
    obj_row_idx: Optional[int] = None
    con_orig: list[int] = []
    for i, rt in enumerate(row_types):
        if rt == "N":
            if obj_row_idx is None:
                obj_row_idx = i
        else:
            con_orig.append(i)

    m = len(con_orig)
    n = len(col_names)
    row_remap = {orig: new for new, orig in enumerate(con_orig)}

    c = np.zeros(n, dtype=np.float64)
    for j, v in obj_c.items():
        c[j] = v
    if sense == "max":
        c = -c

    A = np.zeros((m, n), dtype=np.float64)
    for (orig_r, col_j, val) in entries:
        if orig_r in row_remap:
            A[row_remap[orig_r], col_j] = val

    row_lo_arr = np.full(m, -INF)
    row_hi_arr = np.full(m, INF)
    for new_i, orig_i in enumerate(con_orig):
        rt = row_types[orig_i]
        rhs = rhs_map.get(orig_i, 0.0)
        rng = ranges_map.get(orig_i)
        if rt == "E":
            row_lo_arr[new_i] = row_hi_arr[new_i] = rhs
            if rng is not None:
                if rng > 0: row_hi_arr[new_i] = rhs + rng
                elif rng < 0: row_lo_arr[new_i] = rhs + rng
        elif rt == "G":
            row_lo_arr[new_i] = rhs
            if rng: row_hi_arr[new_i] = rhs + abs(rng)
        elif rt == "L":
            row_hi_arr[new_i] = rhs
            if rng: row_lo_arr[new_i] = rhs - abs(rng)

    obj_const = 0.0
    if obj_row_idx is not None:
        raw_rhs = rhs_map.get(obj_row_idx, 0.0)
        obj_const = -raw_rhs if sense == "min" else raw_rhs

    con_names = [row_names[i] for i in con_orig]
    col_lo_arr = np.array([col_lo.get(j, 0.0) for j in range(n)])
    col_hi_arr = np.array([col_hi.get(j, INF) for j in range(n)])
    integ_arr = np.array([integ.get(j, 0) for j in range(n)], dtype=np.int8)

    return MinModel(
        nrows=m, ncols=n,
        c=c, A_dense=A,
        row_lo=row_lo_arr, row_hi=row_hi_arr,
        col_lo=col_lo_arr, col_hi=col_hi_arr,
        integrality=integ_arr,
        sense=sense, obj_const=obj_const,
        row_names=con_names, col_names=col_names,
        sha256=sha, source_path=str(path),
    )
