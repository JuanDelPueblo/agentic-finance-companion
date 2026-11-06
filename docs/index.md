# Agentic Finance Companion

The capstone aims to help students and early-career adults with irregular income
build a financial plan. The planned flow connects accounts through Plaid, computes
financial state, and validates a plan drafted by an LLM.

## Current starter

The React frontend calls `GET /api/health`. FastAPI checks its PostgreSQL connection
and reports the result. A separate worker process starts alongside the API and waits
for shutdown. The schema and PostgreSQL-backed job processing are deferred.

## Planned architecture

```text
Browser ──► React app ──/api──► FastAPI backend ──► PostgreSQL
                                     ├──► OpenID Connect provider
                                     ├──► Plaid
                                     └──► LLM provider
```

## Repository layout

| Path | Contents |
|---|---|
| `backend/` | FastAPI app, worker entry point, tests, and `openapi.json` |
| `frontend/` | React app and tests |
| `docs/` | This site |
| `compose.yaml` | PostgreSQL, API, worker, and frontend for local development |
| `.env.example` | Local PostgreSQL settings |
