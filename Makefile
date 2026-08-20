SHELL := /bin/sh

PYTHON ?= python3.12
PROJECT_NPM ?= ../scripts/npm11.sh
LEGACY_SOURCE_DIR ?= ../extraction/export/uv_print_full/tables
IMPORT_PROFILE_OUTPUT ?= artifacts/import/profile
IMPORT_FREEZE_OUTPUT ?= artifacts/import/freeze/legacy_import_freeze.json
IMPORT_FULL_DRY_RUN_OUTPUT ?= artifacts/import/full-dry-run/legacy_full_dry_run.json
COMPOSE_PARSE_ENV = POSTGRES_PASSWORD=company-system-compose-parse-only

.PHONY: bootstrap env-check dev down lint test build audit check shell-check \
	docs-check toolchain-check env-init db-config db-up db-down db-status \
	db-test-config db-test-up db-test-down backend-database-integration-check \
	import-profile import-profile-test backend-test backend-check frontend-test \
	frontend-lint frontend-build frontend-audit frontend-check backend-build \
	seed-test-identity import-customers-dry-run import-master-data-dry-run \
	import-freeze \
	import-full-dry-run import-full-dry-run-test \
	import-work-items-dry-run import-quotations-dry-run \
	import-work-orders-dry-run import-inventory-dry-run \
	import-shipments-dry-run import-pricing-dry-run import-billing-dry-run

bootstrap:
	PYTHON_BIN=$(PYTHON) ./scripts/bootstrap.sh

env-check:
	./scripts/check-local-env.sh

dev: env-check
	./scripts/dev.sh

down:
	$(COMPOSE_PARSE_ENV) docker compose --profile test down --remove-orphans

lint: docs-check shell-check db-config
	cd backend && .venv/bin/ruff check app scripts tests
	cd frontend && $(PROJECT_NPM) run lint
	cd frontend && $(PROJECT_NPM) run api:check

test: docs-check import-profile-test backend-check backend-database-integration-check frontend-test

build: backend-build frontend-build

audit: frontend-audit
	cd backend && .venv/bin/python -m pip check

check: lint test build audit

docs-check:
	./scripts/check-project-docs.sh

toolchain-check:
	NODE_BIN=./scripts/node24.sh NPM_BIN=./scripts/npm11.sh PYTHON_BIN=$(PYTHON) \
		./scripts/check-toolchain.sh

env-init:
	@test -f .env || cp .env.example .env
	@echo "Local .env is present. Replace the placeholder password before shared use."

db-config:
	$(COMPOSE_PARSE_ENV) docker compose config --quiet

db-up: env-check
	docker compose up -d postgres

db-down:
	docker compose down

db-status:
	docker compose ps postgres

seed-test-identity: env-check
	cd backend && .venv/bin/python scripts/seed_test_identity.py

db-test-config:
	$(COMPOSE_PARSE_ENV) docker compose --profile test config --quiet

db-test-up:
	$(COMPOSE_PARSE_ENV) docker compose --profile test up -d --wait postgres-test

db-test-down:
	$(COMPOSE_PARSE_ENV) docker compose --profile test stop postgres-test

backend-database-integration-check:
	@set -eu; \
	cleanup() { $(COMPOSE_PARSE_ENV) docker compose --profile test stop postgres-test >/dev/null; }; \
	trap cleanup EXIT INT TERM; \
	$(COMPOSE_PARSE_ENV) docker compose --profile test up -d --wait postgres-test; \
	RUN_DATABASE_INTEGRATION=1 backend/.venv/bin/python -m pytest \
		-c backend/pyproject.toml backend/tests -m database_integration

import-profile:
	$(PYTHON) scripts/legacy_import_profile.py \
		--source-dir "$(LEGACY_SOURCE_DIR)" \
		--output-dir "$(IMPORT_PROFILE_OUTPUT)"

import-profile-test:
	$(PYTHON) -m unittest discover -s scripts/tests -p 'test_*.py' -v

import-freeze:
	$(PYTHON) scripts/legacy_import_freeze.py \
		--source-dir "$(LEGACY_SOURCE_DIR)" \
		--output-file "$(IMPORT_FREEZE_OUTPUT)"

import-full-dry-run:
	$(PYTHON) scripts/legacy_full_dry_run.py \
		--source-dir "$(LEGACY_SOURCE_DIR)" \
		--freeze-report "$(IMPORT_FREEZE_OUTPUT)" \
		--output-file "$(IMPORT_FULL_DRY_RUN_OUTPUT)"

import-full-dry-run-test: db-test-up
	cd backend && .venv/bin/python scripts/run_legacy_full_dry_run.py \
		--source-dir "../../extraction/export/uv_print_full/tables" \
		--freeze-report "../$(IMPORT_FREEZE_OUTPUT)" \
		--output-file "../$(IMPORT_FULL_DRY_RUN_OUTPUT)"

import-customers-dry-run:
	$(PYTHON) scripts/legacy_customer_dry_run.py \
		--source-file "$(LEGACY_SOURCE_DIR)/cust.csv" \
		--output-file "artifacts/import/customers/cust_dry_run.json"

import-master-data-dry-run:
	$(PYTHON) scripts/legacy_master_data_dry_run.py \
		--source-dir "$(LEGACY_SOURCE_DIR)" \
		--output-file "artifacts/import/master-data/master_data_dry_run.json"

import-work-items-dry-run:
	$(PYTHON) scripts/legacy_work_items_dry_run.py \
		--source-file "$(LEGACY_SOURCE_DIR)/wpa.csv" \
		--customer-file "$(LEGACY_SOURCE_DIR)/cust.csv" \
		--output-file "artifacts/import/work-items/wpa_dry_run.json"

import-quotations-dry-run:
	$(PYTHON) scripts/legacy_quotation_dry_run.py \
		--source-dir "$(LEGACY_SOURCE_DIR)" \
		--output-file "artifacts/import/quotations/b_replay_dry_run.json"

import-work-orders-dry-run:
	$(PYTHON) scripts/legacy_work_order_dry_run.py \
		--source-dir "$(LEGACY_SOURCE_DIR)" \
		--output-file "artifacts/import/work-orders/subpoena_quote_dry_run.json"

import-inventory-dry-run:
	$(PYTHON) scripts/legacy_inventory_dry_run.py \
		--source-dir "$(LEGACY_SOURCE_DIR)" \
		--output-file "artifacts/import/inventory/merchandise_dry_run.json"

import-shipments-dry-run:
	$(PYTHON) scripts/legacy_shipment_dry_run.py \
		--source-dir "$(LEGACY_SOURCE_DIR)" \
		--output-file "artifacts/import/shipments/subp_sale_dry_run.json"

import-pricing-dry-run:
	$(PYTHON) scripts/legacy_pricing_dry_run.py \
		--source-dir "$(LEGACY_SOURCE_DIR)" \
		--output-file "artifacts/import/pricing/sal_dry_run.json"

import-billing-dry-run:
	$(PYTHON) scripts/legacy_billing_dry_run.py \
		--source-dir "$(LEGACY_SOURCE_DIR)" \
		--output-file "artifacts/import/billing/rec_income_dry_run.json"

backend-test:
	cd backend && .venv/bin/python -m pytest -m "not database_integration"

backend-check: backend-test
	cd backend && .venv/bin/python -m compileall -q app scripts tests
	cd backend && .venv/bin/python -m pip check

frontend-test:
	cd frontend && $(PROJECT_NPM) test
	cd frontend && $(PROJECT_NPM) run api:check

frontend-lint:
	cd frontend && $(PROJECT_NPM) run lint

frontend-build:
	cd frontend && $(PROJECT_NPM) run typecheck
	cd frontend && $(PROJECT_NPM) run build

frontend-audit:
	cd frontend && $(PROJECT_NPM) audit --audit-level=high

frontend-check: frontend-test
	$(MAKE) frontend-lint frontend-build frontend-audit

backend-build:
	cd backend && .venv/bin/python -m compileall -q app scripts
	cd backend && APP_ENV=test APP_HOST=127.0.0.1 APP_PORT=8000 \
		APP_PUBLIC_ORIGIN='http://testserver' \
		CSRF_HMAC_KEY='dGVzdC1vbmx5LWNzcmYta2V5LTMyLWJ5dGVzISEhISE' \
		AUTH_SECURITY_HMAC_KEY='dGVzdC1vbmx5LWF1dGgta2V5LTMyLWJ5dGVzISEhISE' \
		DATABASE_URL='postgresql+psycopg://company_system_test:build-only@127.0.0.1/company_system_test' \
		.venv/bin/python -c 'from app.main import app; assert app.title'

shell-check:
	bash -n scripts/*.sh
