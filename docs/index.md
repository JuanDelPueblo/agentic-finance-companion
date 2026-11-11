# Agentic Finance Companion

The capstone aims to help students and early-career adults with irregular income
build a financial plan. The planned flow connects accounts through Plaid, computes
financial state, and validates a plan drafted by an LLM.

## Current state

Preliminary frontend prototype implemented. The prototype uses synthetic financial data to exercise onboarding, income and recurring expense entry, financial plan creation and comparison, and dashboard navigation.

The backend works end to end on Plaid Sandbox data: a user registers, signs in, links a
Sandbox bank, and reads their financial state from the API.

| Part | State |
|---|---|
| Accounts and sign-in | Done: email registration and login with a JWT access token |
| Plaid linking, transaction sync, and webhooks | Done on Plaid Sandbox |
| Financial-state calculations | Done: six endpoints under `/api/financial-state` |
| LLM adapter | Done: Anthropic and OpenAI, with validated structured replies |
| Plan generation and validation | Not started |
| Missing-context detection and replanning | Not started |
| Web interface | Prototype with synthetic data, not yet connected to the API |

## Project links

- [Source code](https://github.com/JuanDelPueblo/agentic-finance-companion)
- [Test runs](https://github.com/JuanDelPueblo/agentic-finance-companion/actions/workflows/ci.yml)

## Team

Edyan A. Cruz Vélez, Julio Camacho, and Ángel A. Martínez Maldonado. Capstone project,
University of Puerto Rico at Mayagüez, Fall 2026. Advisor: Fernando Torre.

## Architecture

```text
Browser ──► React app ──/api──► FastAPI backend ──► PostgreSQL
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
