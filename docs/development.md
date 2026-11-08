# Development

## API contract

FastAPI generates the OpenAPI document from the backend routes and response models.
The frontend generates TypeScript types from that document.

```text
backend/app/ ──► backend/openapi.json ──► frontend/src/api/schema.d.ts
```

After you change a schema or route:

1. From the repo root, run `cd backend && uv run python scripts/export_openapi.py`.
2. From the repo root, run `cd frontend && npm ci && npm run generate:api`.
3. Fix any frontend type errors (`cd frontend && npm run typecheck`).
4. Commit the regenerated files with your change.

CI fails if the committed files are out of date, or if the frontend no longer
type-checks against them. While the backend runs, you can browse and try the API at
[localhost:8000/docs](http://localhost:8000/docs).

## Checks

| Suite | Command |
|---|---|
| Backend lint and format | `cd backend && uv run ruff check . && uv run ruff format --check .` |
| Backend tests | `cd backend && uv run pytest` |
| Frontend | `cd frontend && npm test` |
| End-to-end | `cd frontend && npx playwright test` |

Most backend tests need a real PostgreSQL database. Without one, `pytest` skips them, so
run them before you open a pull request. CI always runs them. With the Compose stack
running, create a separate test database once, then point the tests at it:

```sh
docker compose exec db createdb -U finance finance_test
cd backend
TEST_DATABASE_URL=postgresql+psycopg://finance:finance@localhost:5432/finance_test uv run pytest
```

The test database name must end in `_test`. Each test run drops and recreates its schema,
then applies every Alembic migration. Each test rolls back its own changes.

The frontend and end-to-end tests use simulated API responses and need no containers or
credentials.

## Documentation site

MkDocs reads `mkdocs.yml` and builds the pages in `docs/`. Run the same strict build
as CI from the repository root.

```sh
uvx --with-requirements docs/requirements.txt mkdocs build --strict
```
