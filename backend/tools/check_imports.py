#!/usr/bin/env python3
"""
tools/check_imports.py
======================
Sovereignty audit for the NIRBHAR solver core.

Scans nirbhar/ and nirbhar_verify/ via AST and enforces:
  1. No forbidden solver/numeric libraries imported inside nirbhar/ or nirbhar_verify/
     (no scipy, cvxpy, highspy, or-tools, pulp, pyomo, mpax, glpk, gurobi, cplex, xpress)
  2. nirbhar_verify/ imports NOTHING from nirbhar/
  3. nirbhar/ does not import nirbhar_verify/ (one-way isolation)

Allowed inside nirbhar/ and nirbhar_verify/:
  stdlib, numpy, numba, jax (and their submodules)

Run:
  python tools/check_imports.py              → exit 0 if clean, exit 1 if violations
  python tools/check_imports.py --json       → also emit machine-readable JSON
"""

import ast
import json
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN_IN_SOLVER = {
    "scipy", "cvxpy", "highspy", "highs", "ortools", "pulp",
    "pyomo", "mpax", "glpk", "gurobipy", "cplex", "xpress",
    "cylp", "pyscipopt", "mip", "linprog", "clarabel",
    "quadprog", "osqp", "ecos", "scs",
}

ALLOWED_IN_SOLVER = {
    # stdlib — we allow everything from stdlib by not listing it; we only block specific names
    "numpy", "np",     # always allowed
    "numba",           # always allowed
    "jax",             # always allowed
}

SOLVER_DIRS = ["nirbhar", "nirbhar_verify"]


def is_forbidden(module_name: str) -> bool:
    """Return True if the top-level package of module_name is forbidden."""
    top = module_name.split(".")[0].lower()
    return top in FORBIDDEN_IN_SOLVER


def is_cross_import(module_name: str, source_pkg: str) -> str | None:
    """
    Return a description if a file in source_pkg imports from a forbidden cross-package.
    nirbhar_verify must not import nirbhar.
    nirbhar must not import nirbhar_verify.
    """
    top = module_name.split(".")[0]
    if source_pkg == "nirbhar_verify" and top == "nirbhar":
        return f"nirbhar_verify imports from nirbhar (isolation violated)"
    if source_pkg == "nirbhar" and top == "nirbhar_verify":
        return f"nirbhar imports from nirbhar_verify"
    return None


def scan_file(path: Path, source_pkg: str) -> list[dict]:
    """Parse one Python file and return list of violation dicts."""
    violations: list[dict] = []
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as e:
        violations.append({
            "file": str(path.relative_to(ROOT)),
            "line": e.lineno,
            "issue": f"SyntaxError: {e.msg}",
        })
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if is_forbidden(name):
                    violations.append({
                        "file": str(path.relative_to(ROOT)),
                        "line": node.lineno,
                        "issue": f"Forbidden import: {name!r}",
                    })
                cross = is_cross_import(name, source_pkg)
                if cross:
                    violations.append({
                        "file": str(path.relative_to(ROOT)),
                        "line": node.lineno,
                        "issue": cross,
                    })

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if is_forbidden(module):
                violations.append({
                    "file": str(path.relative_to(ROOT)),
                    "line": node.lineno,
                    "issue": f"Forbidden import: from {module!r}",
                })
            cross = is_cross_import(module, source_pkg)
            if cross:
                violations.append({
                    "file": str(path.relative_to(ROOT)),
                    "line": node.lineno,
                    "issue": cross,
                })

    return violations


def run_audit(emit_json: bool = False) -> int:
    all_violations: list[dict] = []
    files_scanned = 0

    for pkg in SOLVER_DIRS:
        pkg_dir = ROOT / pkg
        if not pkg_dir.exists():
            continue
        for py_file in sorted(pkg_dir.rglob("*.py")):
            files_scanned += 1
            violations = scan_file(py_file, pkg)
            all_violations.extend(violations)

    if emit_json:
        result = {
            "files_scanned": files_scanned,
            "violations": len(all_violations),
            "details": all_violations,
        }
        print(json.dumps(result, indent=2))
    else:
        if all_violations:
            print(f"\n[FAIL]  check_imports FAILED — {len(all_violations)} violation(s) in {files_scanned} files\n")
            for v in all_violations:
                print(f"  {v['file']}:{v['line']}  →  {v['issue']}")
            print()
        else:
            print(f"\n[PASS]  check_imports PASSED — {files_scanned} files scanned, 0 violations.\n")
            print("Sovereignty rules enforced:")
            print("  [OK] nirbhar/ imports no forbidden solver/numeric library")
            print("  [OK] nirbhar/ does not import from nirbhar_verify/")
            print("  [OK] nirbhar_verify/ imports nothing from nirbhar/")
            print("  [OK] nirbhar_verify/ imports no forbidden solver/numeric library")
            print()

    return 1 if all_violations else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="NIRBHAR sovereignty import checker")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()
    sys.exit(run_audit(emit_json=args.json))


if __name__ == "__main__":
    main()
