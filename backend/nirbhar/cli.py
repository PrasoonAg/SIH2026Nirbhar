"""
nirbhar/cli.py
==============
Command-line interface for the NIRBHAR optimization solver (§6.11).
Subcommands:
  nirbhar solve <path.mps>      Solve LP, MILP, or QP model with certification
  nirbhar verify <mps> <cert>   Independently verify certificate
  nirbhar industrial            Generate and solve MRPL Refinery planning model
  nirbhar bench                 Run benchmark suite across standard models
"""

from __future__ import annotations
import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

from nirbhar.io.mps import parse_mps
from nirbhar.lp.dual_simplex import dual_simplex_solve, DSSOptions, LPResult, FarkasRay, UnboundedRay
from nirbhar.ipm.mehrotra import mehrotra_ipm, IPMOptions
from nirbhar.robust.controller import dispatch_solve, RobustOptions
from nirbhar.mip.bb import branch_and_cut_solve, BCOptions
from nirbhar.qp.mehrotra_qp import qp_solve, QPOptions
from nirbhar.qp.outer_approx import outer_approximation_miqp, MIQPOptions
from nirbhar.certificate.builder import build_certificate
from nirbhar.explain.report import generate_explanation_report
from nirbhar.industrial.refinery import build_refinery_model
import subprocess


def cmd_solve(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.exists():
        print(f"Error: Model file '{path}' not found.", file=sys.stderr)
        return 1

    t0 = time.perf_counter()
    model = parse_mps(path)
    t_parse = time.perf_counter() - t0

    if not args.json:
        print(f"===============================================================")
        print(f" NIRBHAR Solver - Sovereign Optimization Core (SIH26119)")
        print(f"===============================================================")
        print(f" Model       : {path.name}")
        print(f" Dimensions  : {model.nrows} rows, {model.ncols} cols, {model.nnz} nonzeros")
        print(f" Class       : {model.problem_class}")
        print(f" Sense       : {model.sense}")
        print(f" Parse Time  : {t_parse * 1000:.2f} ms")
        print(f" Dispatching : {args.method.upper()}")
        print(f"---------------------------------------------------------------")

    t_solve_0 = time.perf_counter()
    method = args.method.lower()

    if method == "auto":
        if model.is_miqp:
            res = outer_approximation_miqp(model, MIQPOptions(verbose=args.verbose))
            solve_path = ["outer-approximation", "miqp-kelley"]
        elif model.is_qp:
            res = qp_solve(model, QPOptions(verbose=args.verbose))
            solve_path = ["mehrotra-ipm", "qp-interior-point"]
        elif model.is_milp:
            res = branch_and_cut_solve(model, BCOptions())
            solve_path = ["branch-and-cut", "mip-tree"]
        else:
            # Linear Program: RobustController
            s_res = dispatch_solve(model, RobustOptions(verbose=args.verbose))
            res = s_res.inner
            solve_path = [f"robust-level-{s_res.level_used}"]
    elif method == "simplex":
        res = dual_simplex_solve(model, opts=DSSOptions(verbose=args.verbose))
        solve_path = ["dual-simplex"]
    elif method == "ipm":
        if model.is_qp:
            res = qp_solve(model, QPOptions(verbose=args.verbose))
            solve_path = ["qp-ipm"]
        else:
            res = mehrotra_ipm(model, opts=IPMOptions(verbose=args.verbose))
            solve_path = ["mehrotra-ipm"]
    elif method == "bc":
        res = branch_and_cut_solve(model, BCOptions())
        solve_path = ["branch-and-cut"]
    elif method == "oa":
        res = outer_approximation_miqp(model, MIQPOptions(verbose=args.verbose))
        solve_path = ["outer-approximation"]
    elif method == "hpr":
        from nirbhar.hpr.hpr_solver import hpr_solve, HPROptions
        res = hpr_solve(model, HPROptions(verbose=args.verbose))
        solve_path = ["gpu-hpr-first-order"]
    elif method == "crossover":
        from nirbhar.hpr.hpr_solver import hpr_solve, HPROptions
        from nirbhar.crossover.crossover import crossover_solve
        h_res = hpr_solve(model, HPROptions(verbose=args.verbose))
        xo = crossover_solve(model, h_res.x, h_res.y)
        res = LPResult(
            status=xo.status, x=xo.x, y=xo.y,
            z_primal=xo.z_primal, z_dual=xo.z_dual, gap=xo.gap,
            iters=h_res.iters + xo.polish_iters, msg="HPR with Basis Crossover"
        )
        solve_path = ["hpr-crossover-vertex-polish"]
    elif method == "race":
        from nirbhar.robust.controller import concurrent_root_race
        s_res = concurrent_root_race(model, verbose=args.verbose)
        res = s_res.inner
        solve_path = ["concurrent-root-race"]
    elif method == "parallel-bc":
        from nirbhar.mip.parallel_bb import parallel_branch_and_cut_solve, ParallelBCOptions
        res = parallel_branch_and_cut_solve(model, ParallelBCOptions())
        solve_path = ["deterministic-parallel-branch-and-cut"]
    elif method == "robust":
        s_res = dispatch_solve(model, RobustOptions(verbose=args.verbose))
        res = s_res.inner
        solve_path = [f"robust-level-{s_res.level_used}"]
    else:
        print(f"Error: Unknown method '{args.method}'", file=sys.stderr)
        return 1

    t_solve = time.perf_counter() - t_solve_0

    status = getattr(res, "status", "UNKNOWN")
    obj_val = getattr(res, "z_primal", getattr(res, "objective", math.nan))
    bound_val = getattr(res, "z_dual", getattr(res, "lower_bound", math.nan))
    gap_val = getattr(res, "gap", math.nan)
    iters = getattr(res, "iters", getattr(res, "iterations", 0))

    if args.json:
        out = {
            "model": str(path.name),
            "status": status,
            "objective": obj_val if math.isfinite(obj_val) else None,
            "lower_bound": bound_val if math.isfinite(bound_val) else None,
            "gap": gap_val if math.isfinite(gap_val) else None,
            "iterations": iters,
            "solve_time_s": t_solve,
            "parse_time_s": t_parse,
            "solve_path": solve_path,
        }
        print(json.dumps(out, indent=2))
    else:
        print(f" Status      : {status}")
        if math.isfinite(obj_val):
            print(f" Objective   : {obj_val:.8f}")
        if math.isfinite(bound_val):
            print(f" Lower Bound : {bound_val:.8f}")
        if math.isfinite(gap_val):
            print(f" Rel Gap     : {gap_val:.4e}")
        print(f" Iterations  : {iters}")
        print(f" Solve Time  : {t_solve * 1000:.2f} ms")
        print(f" Solve Path  : {' -> '.join(solve_path)}")
        print(f"---------------------------------------------------------------")
        report = generate_explanation_report(model, res, timing_s=t_solve, solve_path=solve_path)
        print(f" Explain     : {report.headline}")
        print(f" Summary     : {report.summary}")
        print(f"===============================================================")

    if args.cert:
        cert_path = Path(args.cert)
        cert = build_certificate(model, res, timing_s=t_solve, solve_path=solve_path)
        cert_path.write_text(json.dumps(cert, indent=2), encoding="utf-8")
        if not args.json:
            print(f" Certificate : Saved to {cert_path}")

    return 0 if status in ("OPTIMAL", "OPTIMAL_WITHIN_GAP") else 2


def cmd_verify(args: argparse.Namespace) -> int:
    mps_path = Path(args.mps)
    cert_path = Path(args.cert)

    if not mps_path.exists():
        print(f"Error: Model file '{mps_path}' not found.", file=sys.stderr)
        return 1
    if not cert_path.exists():
        print(f"Error: Certificate file '{cert_path}' not found.", file=sys.stderr)
        return 1

    # Isolated verifier execution (zero imports from nirbhar_verify inside nirbhar)
    cmd = [sys.executable, "-m", "nirbhar_verify.cli", str(mps_path), str(cert_path)]
    backend_root = str(Path(__file__).resolve().parent.parent)
    env = dict(os.environ)
    env["PYTHONPATH"] = backend_root + (os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else "")
    p = subprocess.run(cmd, env=env)
    return p.returncode


def cmd_industrial(args: argparse.Namespace) -> int:
    periods = args.periods
    p_class = args.class_
    scenario = args.scenario

    print(f"===============================================================")
    print(f" NIRBHAR Industrial - MRPL Refinery Production Optimizer")
    print(f"===============================================================")
    print(f" Problem Class : {p_class}")
    print(f" Schedule      : {periods} Operating Periods")
    print(f" Scenario      : {scenario}")
    print(f"---------------------------------------------------------------")

    model = build_refinery_model(periods=periods, problem_class=p_class, scenario=scenario)
    print(f" Matrix        : {model.nrows} rows, {model.ncols} cols, {model.nnz} nonzeros")

    t0 = time.perf_counter()
    if p_class == "QP":
        res = qp_solve(model)
        grm = -res.z_primal
    elif p_class == "MILP":
        res = branch_and_cut_solve(model, BCOptions(max_nodes=100))
        grm = -res.objective
    else:
        res = dual_simplex_solve(model)
        grm = -res.z_primal

    t_solve = time.perf_counter() - t0

    print(f" Optimize Status: {res.status}")
    print(f" Gross Refining Margin (GRM) : ${grm:,.2f}")
    print(f" Solve Time                  : {t_solve * 1000:.2f} ms")
    print(f"===============================================================")

    if args.export:
        exp_path = Path(args.export)
        from nirbhar.io.writer import write_mps
        write_mps(model, exp_path)
        print(f" Exported model to {exp_path}")

    return 0


def cmd_bench(args: argparse.Namespace) -> int:
    from pathlib import Path
    data_manifest = Path(__file__).resolve().parent.parent / "data" / "manifest.json"
    if not data_manifest.exists():
        data_manifest = Path(__file__).resolve().parent.parent.parent / "data" / "manifest.json"

    if not data_manifest.exists():
        print(f"Error: manifest.json not found at {data_manifest}", file=sys.stderr)
        return 1

    manifest = json.loads(data_manifest.read_text(encoding="utf-8"))
    models = manifest.get("models", [])
    tier = args.tier.lower()

    if tier == "t1":
        selected = [m for m in models if m.get("tier", "").startswith("T1") and m.get("class_") == "LP"]
    elif tier == "qp":
        selected = [m for m in models if m.get("class_") == "QP"]
    else:
        selected = [m for m in models if m.get("tier", "").startswith("T1")][:10]

    if args.limit:
        selected = selected[:args.limit]

    print(f"==========================================================================")
    print(f" NIRBHAR Benchmark Suite - {len(selected)} Models (Tier: {tier.upper()})")
    print(f"==========================================================================")
    print(f"{'Model':<18} {'Class':<5} {'Rows':<6} {'Cols':<6} {'Status':<10} {'Time(ms)':<10} {'Obj Error':<12}")
    print(f"--------------------------------------------------------------------------")

    base_dir = data_manifest.parent
    passed = 0

    for entry in selected:
        m_path = base_dir / entry["file"]
        if not m_path.exists():
            continue
        model = parse_mps(m_path)
        t0 = time.perf_counter()
        if model.is_qp:
            res = qp_solve(model)
            obj = res.z_primal
        else:
            res = dual_simplex_solve(model)
            obj = res.z_primal
        t_ms = (time.perf_counter() - t0) * 1000

        ref = entry.get("reference_objective", math.nan)
        err = abs(obj - ref) if math.isfinite(obj) and math.isfinite(ref) else math.nan

        print(f"{entry['name']:<18} {entry['class_']:<5} {model.nrows:<6} {model.ncols:<6} {res.status:<10} {t_ms:<10.1f} {err:<12.2e}")
        if res.status == "OPTIMAL" and (not math.isfinite(ref) or err < 1e-4):
            passed += 1

    print(f"--------------------------------------------------------------------------")
    print(f" Result: {passed}/{len(selected)} passed successfully.")
    print(f"==========================================================================")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="nirbhar",
        description="NIRBHAR - Sovereign Certified Hybrid CPU-GPU Optimization Solver Core (PS SIH26119)",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # 1. solve
    p_solve = subparsers.add_parser("solve", help="Solve an optimization model (.mps/.qps)")
    p_solve.add_argument("path", help="Path to MPS/QPS model file")
    p_solve.add_argument("--method", "--engine", dest="method", choices=["auto", "simplex", "ipm", "bc", "oa", "robust", "hpr", "crossover", "race", "parallel-bc"], default="auto")
    p_solve.add_argument("--cert", "--out", dest="cert", help="Output path for verification certificate (.json)")
    p_solve.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p_solve.add_argument("--verbose", action="store_true", help="Print iteration progress")
    p_solve.set_defaults(func=cmd_solve)

    # 2. verify
    p_verify = subparsers.add_parser("verify", help="Independently verify a solve certificate")
    p_verify.add_argument("mps", help="Path to original MPS model file")
    p_verify.add_argument("cert", help="Path to certificate JSON file")
    p_verify.set_defaults(func=cmd_verify)

    # 3. industrial
    p_ind = subparsers.add_parser("industrial", help="MRPL Refinery multi-period planning demo")
    p_ind.add_argument("--periods", type=int, default=4, help="Number of operating periods (default: 4)")
    p_ind.add_argument("--class", dest="class_", choices=["LP", "MILP", "QP"], default="LP", help="Problem class")
    p_ind.add_argument("--scenario", choices=["baseline", "tight-sulfur", "crude-shock", "diesel-surge"], default="baseline")
    p_ind.add_argument("--export", help="Export generated model to MPS file")
    p_ind.set_defaults(func=cmd_industrial)

    # 4. bench
    p_bench = subparsers.add_parser("bench", help="Run benchmark suite")
    p_bench.add_argument("--tier", choices=["t1", "t2", "qp", "all"], default="t1")
    p_bench.add_argument("--limit", type=int, default=None)
    p_bench.set_defaults(func=cmd_bench)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
