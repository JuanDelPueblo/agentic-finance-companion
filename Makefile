.PHONY: setup lint test openapi check docs

# Create .env from the example (if missing) and install host dependencies.
setup:
	test -f .env || cp .env.example .env
	cd backend && uv sync
	cd frontend && npm ci

lint:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app scripts tests
	cd frontend && npm run lint && npm run typecheck

test:
	cd backend && uv run pytest
	cd frontend && npm test

# Regenerate backend/openapi.json and the frontend types generated from it.
openapi:
	cd backend && uv run python scripts/export_openapi.py
	cd frontend && npm run generate:api

# Run what CI runs. Fails if the committed API contract is out of date.
check: lint test openapi docs
	git diff --exit-code -- backend/openapi.json frontend/src/api/schema.d.ts

docs:
	uvx --with-requirements docs/requirements.txt mkdocs build --strict
