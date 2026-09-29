"""Helper script to run import-linter with the src/ directory on sys.path."""
import sys
import os

# Ensure src/ is on the path before import-linter tries to find pramana
src = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
sys.path.insert(0, os.path.abspath(src))

from importlinter.cli import lint_imports_command  # noqa: E402
try:
    lint_imports_command(standalone_mode=True)
except SystemExit as e:
    sys.exit(e.code)
