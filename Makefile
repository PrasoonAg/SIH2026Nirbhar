.PHONY: setup test arch inv selfaudit openapi web bundle verify-offline predemo help

BACKEND_DIR := backend
PYTHON := python3
PYTEST  := $(PYTHON) -m pytest
UV      := uv

# ─── Dev setup ───────────────────────────────────────────────────────────────

setup:  ## Install all dev dependencies
	cd $(BACKEND_DIR) && $(UV) pip install -e ".[dev]"
	@echo "Setup complete. Run 'make test' to verify."

# ─── Test targets ─────────────────────────────────────────────────────────────

test:  ## Run all backend tests (unit + property + contract + arch + integration)
	cd $(BACKEND_DIR) && $(PYTEST) tests/ -v --tb=short

arch:  ## Run architecture tests only (import-linter + structural checks)
	cd $(BACKEND_DIR) && $(PYTEST) tests/architecture/ -v --tb=short
	cd $(BACKEND_DIR) && $(PYTHON) -m importlinter

inv:   ## Check invariant test coverage (warn-only until Phase 8)
	$(PYTHON) scripts/check_inv_coverage.py

inv-strict:  ## Check invariant test coverage — fail on missing (CI Phase 8+)
	$(PYTHON) scripts/check_inv_coverage.py --strict

# ─── Self-audit (Phase 5+) ────────────────────────────────────────────────────

selfaudit:  ## Run the gate self-audit harness
	cd $(BACKEND_DIR) && $(PYTHON) -m pramana.bootstrap.cli selfaudit

# ─── OpenAPI (Phase 1+) ───────────────────────────────────────────────────────

openapi:  ## Export openapi.json and regenerate frontend types
	cd $(BACKEND_DIR) && $(PYTHON) -m pramana.bootstrap.cli export-openapi --out ../frontend/openapi.json
	cd frontend && npx openapi-typescript ../frontend/openapi.json -o src/api/schema.d.ts

# ─── Frontend ─────────────────────────────────────────────────────────────────

web:  ## Build the React frontend (production bundle)
	cd frontend && npm ci && npm run build

# ─── Docker / Compose ─────────────────────────────────────────────────────────

dev-up:  ## Start the dev Compose stack (SQLite mode)
	docker compose -f deploy/compose.yaml up --build

dev-down:  ## Stop the dev Compose stack
	docker compose -f deploy/compose.yaml down

# ─── Offline bundle (Phase 9) ────────────────────────────────────────────────

bundle:  ## Build the offline deployment bundle (connected host)
	bash deploy/bundle/build_bundle.sh

verify-offline:  ## Verify offline compliance from inside running backend container
	docker compose -f deploy/compose.yaml exec backend bash /app/scripts/verify_offline.sh

# ─── Pre-demo gate (Phase 9) ─────────────────────────────────────────────────

predemo: arch inv-strict test selfaudit verify-offline  ## Full pre-demo check (must be green before demo)
	@echo ""
	@echo "✓ predemo gate passed."

# ─── Help ─────────────────────────────────────────────────────────────────────

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*## "}; {printf "  %-18s %s\n", $$1, $$2}'
