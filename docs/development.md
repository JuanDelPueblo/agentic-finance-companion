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

The tests use simulated API or database responses and can run without containers or credentials.

## Documentation site

MkDocs reads `mkdocs.yml` and builds the pages in `docs/`. Run the same strict build
as CI from the repository root.

```sh
uvx --with-requirements docs/requirements.txt mkdocs build --strict
```
