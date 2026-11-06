# Development

## API contract

The backend defines the API with Pydantic schemas in `backend/app/schemas/` and the
routes in `backend/app/api/`. From these, FastAPI generates an OpenAPI document. The
frontend's TypeScript types are generated from that document:

```text
backend/app/schemas/ ──► backend/openapi.json ──► frontend/src/api/schema.d.ts
```

After you change a schema or route:

1. Run `make openapi`. It regenerates both files.
2. Fix any frontend type errors (`cd frontend && npm run typecheck`).
3. Commit the regenerated files with your change.

CI fails if the committed files are out of date, or if the frontend no longer
type-checks against them. While the backend runs, you can browse and try the API at
[localhost:8000/docs](http://localhost:8000/docs).

## Tests

| Suite | Command |
|---|---|
| Backend | `cd backend && uv run pytest` |
| Frontend | `cd frontend && npm test` |
| End-to-end | `cd frontend && npx playwright test` |

No test needs PostgreSQL, a running container, or credentials. External services are
mocked.
