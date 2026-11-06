# Agentic Finance Companion

The app helps students and early-career adults with irregular income build a financial
plan. The user connects bank accounts through Plaid. The backend computes the user's
financial state, asks for missing information, and has an LLM write a plan. A
validator checks each plan before the user sees it.

## Architecture

```text
Browser ──► React app ──/api──► FastAPI backend ──► PostgreSQL
                                     ├──► OpenID Connect provider
                                     ├──► Plaid
                                     └──► LLM provider
```

Only the backend talks to external services. Each service has a mock, so the app runs
without credentials.

## Repository layout

| Path | Contents |
|---|---|
| `backend/` | FastAPI app, tests, `openapi.json` |
| `frontend/` | React app and tests |
| `docs/` | This site |
| `compose.yaml` | PostgreSQL, backend, and frontend for local development |
| `.env.example` | All settings, with comments |
