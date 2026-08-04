SHELL := /bin/sh

PYTHON ?= python3.12
PROJECT_NPM ?= ../scripts/npm11.sh
LEGACY_SOURCE_DIR ?= ../extraction/export/uv_print_full/tables
IMPORT_PROFILE_OUTPUT ?= artifacts/import/profile

.PHONY: docs-check toolchain-check env-init db-config db-up db-down db-status \
	import-profile import-profile-test backend-test backend-check frontend-test \
	frontend-check test

docs-check:
	./scripts/check-project-docs.sh

toolchain-check:
	NODE_BIN=./scripts/node24.sh NPM_BIN=./scripts/npm11.sh PYTHON_BIN=$(PYTHON) \
		./scripts/check-toolchain.sh

env-init:
	@test -f .env || cp .env.example .env
	@echo "Local .env is present. Replace the placeholder password before shared use."

db-config:
	docker compose config --quiet

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

db-status:
	docker compose ps postgres

import-profile:
	$(PYTHON) scripts/legacy_import_profile.py \
		--source-dir "$(LEGACY_SOURCE_DIR)" \
		--output-dir "$(IMPORT_PROFILE_OUTPUT)"

import-profile-test:
	$(PYTHON) -m unittest discover -s scripts/tests -p 'test_*.py' -v

backend-test:
	cd backend && .venv/bin/python -m pytest

backend-check: backend-test
	cd backend && .venv/bin/python -m compileall -q app tests
	cd backend && .venv/bin/python -m pip check

frontend-test:
	cd frontend && $(PROJECT_NPM) test

frontend-check: frontend-test
	cd frontend && $(PROJECT_NPM) run lint
	cd frontend && $(PROJECT_NPM) run typecheck
	cd frontend && $(PROJECT_NPM) run build
	cd frontend && $(PROJECT_NPM) audit --audit-level=high

test: docs-check import-profile-test backend-check frontend-check
