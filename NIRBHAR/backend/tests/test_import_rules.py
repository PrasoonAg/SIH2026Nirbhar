"""
tests/test_import_rules.py
==========================
Sovereignty audit test — runs tools/check_imports.py and asserts exit code 0.
This test always runs (not marked slow) and must pass at the end of every phase.
"""

from __future__ import annotations
import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"


def test_sovereignty_check_passes() -> None:
    """tools/check_imports.py must exit 0 (no sovereignty violations)."""
    script = TOOLS_DIR / "check_imports.py"
    assert script.exists(), f"check_imports.py not found at {script}"
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        cwd=str(TOOLS_DIR.parent),
    )
    assert result.returncode == 0, (
        f"Sovereignty violation detected!\n\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
