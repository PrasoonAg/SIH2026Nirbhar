"""
nirbhar_verify/cli.py
=====================
Command-line interface for the independent, isolated NIRBHAR verifier.
Strictly zero imports from nirbhar/ to guarantee verifier isolation (§7).
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import numpy as np

from nirbhar_verify.mps_min import parse_mps_min
from nirbhar_verify.lp_verify import verify_lp


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="nirbhar-verify",
        description="NIRBHAR Independent Zero-Trust Certificate Verifier (§7)",
    )
    parser.add_argument("mps", help="Path to original MPS model file")
    parser.add_argument("cert", help="Path to solver certificate JSON file")
    parser.add_argument("--tol", type=float, default=1e-6, help="Feasibility tolerance")

    args = parser.parse_args(argv)

    mps_path = Path(args.mps)
    cert_path = Path(args.cert)

    # Allow passing in either order (cert.json model.mps OR model.mps cert.json)
    if mps_path.suffix.lower() == ".json" and cert_path.suffix.lower() in (".mps", ".qps"):
        mps_path, cert_path = cert_path, mps_path

    if not mps_path.exists():
        print(f"Error: MPS model '{mps_path}' not found.", file=sys.stderr)
        return 1
    if not cert_path.exists():
        print(f"Error: Certificate '{cert_path}' not found.", file=sys.stderr)
        return 1

    cert_data = json.loads(cert_path.read_text(encoding="utf-8"))
    status = cert_data.get("status")

    print("===============================================================")
    print(" NIRBHAR Independent Zero-Trust Verifier")
    print("===============================================================")
    print(f" Model       : {mps_path.name}")
    print(f" Certificate : {cert_path.name} (Declared Status: {status})")
    print("---------------------------------------------------------------")

    min_model = parse_mps_min(mps_path)

    if status == "OPTIMAL":
        x = np.array(cert_data.get("solution", {}).get("x", []), dtype=np.float64)
        y = np.array(cert_data.get("solution", {}).get("y", []), dtype=np.float64)
        if len(x) == 0:
            print("Error: Solution vector x missing in certificate.", file=sys.stderr)
            return 1
        if len(y) == 0:
            y = np.zeros(min_model.nrows, dtype=np.float64)

        res = verify_lp(min_model, x, y, primal_tol=args.tol, dual_tol=args.tol)
        print(f" Result             : {res.status}")
        print(f" Primal Feasible    : {res.primal_feas}")
        print(f" Dual Feasible      : {res.dual_feas}")
        print(f" Complementarity OK : {res.cs_ok}")
        print(f" Objective Match    : {res.obj_match}")
        print(f" Verified Obj       : {res.primal_obj:.8f}")
        print(f" Details            : {res.msg}")
        print("===============================================================")
        return 0 if res.is_pass() else 2
    else:
        print(f" Certificate declared non-optimal status: {status}")
        print("===============================================================")
        return 0


if __name__ == "__main__":
    sys.exit(main())
