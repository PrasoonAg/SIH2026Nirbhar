"""
Architecture tests (Phase 0).

Tests in this file run `lint-imports` programmatically and verify structural
invariants that import-linter cannot check (e.g. table prefix ownership,
forbidden call sites, forbidden field names).

Run with: pytest tests/architecture/ -v
Or via:   make arch
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).parent.parent.parent
SRC_ROOT = BACKEND_DIR / "src" / "pramana"


# ─── import-linter contracts ──────────────────────────────────────────────────

def test_import_linter_contracts_pass() -> None:
    """
    All import-linter contracts defined in .importlinter must pass.

    This is the primary enforcement for:
      - Layer boundaries (L0–L6)
      - INV-02 (proposer ↔ trustgate independence)
      - R3 (no framework in domain/)
      - R7 (scoring is pure)

    Note: grimp ≤16.x has a Rust/Python 3.12 incompatibility on Windows.
    If the panic is detected, the test is skipped with a warning.
    Run `make arch` on Linux for the authoritative check.
    """
    import shutil
    import os
    lint_imports_cmd = shutil.which("lint-imports")
    if lint_imports_cmd is None:
        pytest.skip("lint-imports not found on PATH — run `pip install import-linter`")

    env = os.environ.copy()
    existing_pypath = env.get("PYTHONPATH", "")
    src_path = str(BACKEND_DIR / "src")
    env["PYTHONPATH"] = src_path + (os.pathsep + existing_pypath if existing_pypath else "")

    result = subprocess.run(
        [lint_imports_cmd],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        env=env,
    )

    # grimp Rust panic on Python 3.12 / Windows — skip gracefully
    if "pyo3_runtime.PanicException" in result.stdout or "PanicException" in result.stderr:
        pytest.skip(
            "grimp Rust extension panics on Python 3.12 / Windows (upstream bug). "
            "Run `make arch` on Linux for the authoritative import-linter check."
        )

    assert result.returncode == 0, (
        f"import-linter reported violations:\n{result.stdout}\n{result.stderr}"
    )


# ─── Module structure checks ──────────────────────────────────────────────────

MODULES = [
    "shared_kernel",
    "identity",
    "ledger",
    "baseline",
    "crypto",
    "scoring",
    "parsing",
    "proposer",
    "trustgate",
    "profiles",
    "compliance",
    "mapping",
    "ingest",
    "pipeline",
    "sandbox",
    "reporting",
    "federation",
    "bootstrap",
]


@pytest.mark.parametrize("module", MODULES)
def test_module_has_api_py(module: str) -> None:
    """Every module must expose exactly one public surface via api.py (R1)."""
    api_file = SRC_ROOT / module / "api.py"
    assert api_file.exists(), f"{module}/api.py is missing"


@pytest.mark.parametrize("module", MODULES)
def test_module_has_readme(module: str) -> None:
    """Every module must have a README.md (§4 module template)."""
    readme = SRC_ROOT / module / "README.md"
    assert readme.exists(), f"{module}/README.md is missing"


@pytest.mark.parametrize("module", MODULES)
def test_module_has_init(module: str) -> None:
    """Every module must be a package (__init__.py)."""
    init_file = SRC_ROOT / module / "__init__.py"
    assert init_file.exists(), f"{module}/__init__.py is missing"


# ─── Forbidden field names (INV-07) ───────────────────────────────────────────

FORBIDDEN_FIELD_NAMES = ["blended", "confidence_multiplier", "discounted_score"]


@pytest.mark.parametrize("field_name", FORBIDDEN_FIELD_NAMES)
@pytest.mark.inv("INV-07")
def test_no_forbidden_score_fields(field_name: str) -> None:
    """
    INV-07: No blended or discounted score exists anywhere in the codebase.
    Scan all Python source files for forbidden field names as string literals.
    """
    pattern = re.compile(rf"""["\']({re.escape(field_name)})["\']""")
    violations: list[str] = []
    for py_file in SRC_ROOT.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                violations.append(f"{py_file.relative_to(BACKEND_DIR)}:{lineno}: {line.strip()}")
    assert not violations, (
        f"Found forbidden field name '{field_name}' in source:\n" + "\n".join(violations)
    )


# ─── Forbidden imports (INV-09) ───────────────────────────────────────────────

FORBIDDEN_LIVE_PULL_LIBS = ["paramiko", "netmiko", "telnetlib", "napalm", "nornir"]


@pytest.mark.parametrize("lib", FORBIDDEN_LIVE_PULL_LIBS)
@pytest.mark.inv("INV-09")
def test_no_live_pull_imports(lib: str) -> None:
    """INV-09: No SSH/telnet/live-pull libraries imported anywhere."""
    pattern = re.compile(rf"^\s*(import {re.escape(lib)}|from {re.escape(lib)})", re.MULTILINE)
    violations: list[str] = []
    for py_file in SRC_ROOT.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        if pattern.search(text):
            violations.append(str(py_file.relative_to(BACKEND_DIR)))
    assert not violations, (
        f"Found forbidden live-pull import '{lib}' in: {violations}"
    )


# ─── Forbidden eval/exec/pickle on untrusted data (R9) ───────────────────────

FORBIDDEN_CALLS = [r"\beval\(", r"\bexec\(", r"pickle\.loads?\("]


@pytest.mark.parametrize("pattern_str", FORBIDDEN_CALLS)
def test_no_eval_exec_pickle(pattern_str: str) -> None:
    """R9: No eval/exec/pickle on untrusted data anywhere in source."""
    pattern = re.compile(pattern_str)
    violations: list[str] = []
    for py_file in SRC_ROOT.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), start=1):
            # Allow in comments and docstrings heuristically (starts with #)
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if pattern.search(line):
                violations.append(f"{py_file.relative_to(BACKEND_DIR)}:{lineno}: {stripped}")
    assert not violations, (
        f"Found forbidden call '{pattern_str}' in source:\n" + "\n".join(violations)
    )


# ─── ADR files exist ──────────────────────────────────────────────────────────

ADR_FILES = [
    "0001-modular-monolith.md",
    "0002-three-check-gate.md",
    "0003-git-profile-store-db-consistency.md",
]


@pytest.mark.parametrize("adr_file", ADR_FILES)
def test_adr_exists(adr_file: str) -> None:
    """Phase 0 requires ADR-0001, ADR-0002 and ADR-0003."""
    adr_path = BACKEND_DIR.parent / "docs" / "adr" / adr_file
    assert adr_path.exists(), f"Missing ADR: docs/adr/{adr_file}"


# ─── Invariants doc exists ────────────────────────────────────────────────────

def test_invariants_doc_exists() -> None:
    """docs/invariants.md must exist (Phase 0 deliverable)."""
    inv_doc = BACKEND_DIR.parent / "docs" / "invariants.md"
    assert inv_doc.exists(), "docs/invariants.md is missing"


def test_compose_has_internal_core_network() -> None:
    """Compose skeleton must have a core network with internal: true (INV-11)."""
    compose = BACKEND_DIR.parent / "deploy" / "compose.yaml"
    assert compose.exists(), "deploy/compose.yaml is missing"
    text = compose.read_text(encoding="utf-8")
    assert "internal: true" in text, "Compose core network must have internal: true (INV-11)"
