"""
bootstrap.cli — CLI entry-point (argparse-based, Phase 1 skeleton).

Commands:
  db upgrade         — run alembic migrations
  export-openapi     — export OpenAPI JSON
  selfaudit          — run self-audit harness (Phase 5)
  ledger verify      — verify ledger chain (Phase 3)
  profiles verify    — verify Git ↔ DB consistency (Phase 4)
  decay-cycle        — trigger decay sampling (Phase 8)
  keys generate      — generate Ed25519 key pair (Phase 10)
  verify-report      — verify a signed PDF (Phase 10)
  seed-demo          — seed the database with demo data
"""
from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pramana",
        description="PRAMANA network-configuration compliance auditor CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # db upgrade
    db_p = sub.add_parser("db", help="Database management")
    db_sub = db_p.add_subparsers(dest="db_command", required=True)
    db_sub.add_parser("upgrade", help="Run Alembic migrations to head")

    # export-openapi
    openapi_p = sub.add_parser("export-openapi", help="Export OpenAPI schema")
    openapi_p.add_argument("--out", default="openapi.json", help="Output path")

    # selfaudit
    sub.add_parser("selfaudit", help="Run the trust-gate self-audit harness (Phase 5)")

    # ledger verify
    ledger_p = sub.add_parser("ledger", help="Ledger management")
    ledger_sub = ledger_p.add_subparsers(dest="ledger_command", required=True)
    ledger_sub.add_parser("verify", help="Verify the full ledger chain")

    # profiles verify
    profiles_p = sub.add_parser("profiles", help="Profile store management")
    profiles_sub = profiles_p.add_subparsers(dest="profiles_command", required=True)
    profiles_sub.add_parser("verify", help="Verify Git ↔ DB consistency")

    # decay-cycle
    sub.add_parser("decay-cycle", help="Trigger a Provisional mapping decay cycle (Phase 8)")

    # keys generate
    keys_p = sub.add_parser("keys", help="Ed25519 key management (Phase 10)")
    keys_sub = keys_p.add_subparsers(dest="keys_command", required=True)
    keys_sub.add_parser("generate", help="Generate a new Ed25519 key pair")

    # verify-report
    verify_p = sub.add_parser("verify-report", help="Verify a signed PDF report (Phase 10)")
    verify_p.add_argument("pdf", help="Path to the PDF file")
    verify_p.add_argument("sig", help="Path to the signature JSON")
    verify_p.add_argument("--pubkey", required=True, help="Path to the PEM public key")

    # seed-demo
    sub.add_parser("seed-demo", help="Seed the database with demonstration data")

    args = parser.parse_args()

    # ── Dispatch ──────────────────────────────────────────────────────────────
    if args.command == "export-openapi":
        return _export_openapi(args.out)

    print(f"Command '{args.command}' not yet implemented (check phase plan).", file=sys.stderr)
    return 1


def _export_openapi(out: str) -> int:
    try:
        import json
        from pramana.bootstrap.main import app  # type: ignore[import]
        schema = app.openapi()
        with open(out, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2)
        print(f"OpenAPI schema written to {out}")
        return 0
    except Exception as exc:
        print(f"Error exporting OpenAPI: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
