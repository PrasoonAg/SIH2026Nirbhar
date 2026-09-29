#!/usr/bin/env python3
"""
check_inv_coverage.py — verify every invariant (§2) has at least one test.

Usage:
  python scripts/check_inv_coverage.py [--strict]

Behaviour:
  - Scans all *.py files under backend/tests/ for @pytest.mark.inv("INV-xx").
  - Compares against the canonical invariant list in docs/invariants.md.
  - Phase 0–7: WARN only (exit 0) unless --strict is passed.
  - Phase 8+: fails CI if any invariant has no test (exit 1).

Canonical invariant IDs come from the INVARIANTS constant below (synced with §2).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

INVARIANTS = [
    "INV-01",
    "INV-02",
    "INV-03",
    "INV-04",
    "INV-05",
    "INV-06",
    "INV-07",
    "INV-08",
    "INV-09",
    "INV-10",
    "INV-11",
    "INV-12",
    "INV-13",
    "INV-14",
    "INV-15",
    "INV-16",
    "INV-17",
]

# Pattern: @pytest.mark.inv("INV-xx")  or  @pytest.mark.inv('INV-xx')
_INV_PATTERN = re.compile(r"""@pytest\.mark\.inv\(['"](INV-\d+)['"]\)""")


def find_covered_invariants(tests_dir: Path) -> set[str]:
    covered: set[str] = set()
    for py_file in tests_dir.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        for match in _INV_PATTERN.finditer(text):
            covered.add(match.group(1))
    return covered


def main() -> int:
    parser = argparse.ArgumentParser(description="Check invariant test coverage")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if any invariant has no test (used by CI from Phase 8).",
    )
    args = parser.parse_args()

    tests_dir = ROOT / "backend" / "tests"
    if not tests_dir.exists():
        print(f"[check_inv_coverage] tests/ directory not found at {tests_dir}", file=sys.stderr)
        return 1

    covered = find_covered_invariants(tests_dir)
    missing = [inv for inv in INVARIANTS if inv not in covered]

    if missing:
        msg = (
            f"[check_inv_coverage] {len(missing)}/{len(INVARIANTS)} invariants "
            f"have NO test: {', '.join(missing)}"
        )
        if args.strict:
            print(f"FAIL: {msg}", file=sys.stderr)
            return 1
        else:
            print(f"WARN: {msg}")
            print("(warn-only until Phase 8; pass --strict to enforce)")
    else:
        print(
            f"[check_inv_coverage] OK — all {len(INVARIANTS)} invariants have at least one test."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
