# Agentic Finance Companion

A capstone project to help students and early-career adults with irregular income
turn their bank data into a financial plan.

Capstone project, University of Puerto Rico at Mayagüez, Fall 2026.

## Team

| Member | GitHub | Area |
|---|---|---|
| Edyan A. Cruz Vélez | [JuanDelPueblo](https://github.com/JuanDelPueblo) | Infrastructure and integrations |
| Julio Camacho | [CdoxHype](https://github.com/CdoxHype) | Backend and planning engine |
| Ángel A. Martínez Maldonado | [AngelMartinez33](https://github.com/AngelMartinez33) | Frontend and user experience |

## Current state

Preliminary frontend prototype implemented. The prototype uses synthetic financial data to exercise onboarding, income and recurring expense entry, financial plan creation and comparison, and dashboard navigation.

The backend works end to end on Plaid Sandbox data.

| Part | State |
|---|---|
| Accounts and sign-in | Email registration and login. The API issues a JWT access token. |
| Bank data | Plaid account linking, cursor-based transaction sync, and webhooks. |
| Financial state | Six calculations from stored data: available cash, credit balance owed, monthly income, spending, net cash flow, and spending by category. |
| LLM adapter | Structured replies from Anthropic or OpenAI, validated against a schema, with up to two retries. |
| Plan generation and validation | Not started. |
| Web interface | Shows the API and database status only. |

Compose runs the frontend, API, PostgreSQL, and a worker that waits for shutdown.
Alembic manages the database schema. Job processing is planned for later.

## Quick start

Run from the repository root with Docker Compose or Podman Compose.

```sh
docker compose up --build -d   # or: podman compose up --build -d
```

Open the [frontend](http://localhost:5173) or the
[interactive API reference](http://localhost:8000/docs). The stack starts with local
defaults. See the [setup guide](docs/setup.md) for configuration and host commands.

## Database migrations

With Docker Compose and uv installed, run this from the repository root to start
only PostgreSQL, apply the migrations, and verify the schema. For Podman, replace
`docker compose` with `podman compose`.

```sh
docker compose up -d --wait db &&
(
  cd backend &&
  uv run --locked alembic upgrade head &&
  uv run --locked alembic current &&
  uv run --locked alembic check
)
```

The initial migration creates 12 application tables. Alembic also creates
`alembic_version` to track the applied revision.

## Documentation

See [the documentation site](https://juandelpueblo.github.io/agentic-finance-companion/),
or read it in [`docs/`](docs/): [Overview](docs/index.md), [Setup](docs/setup.md), and
[Development](docs/development.md).

## License

Released under the [MIT License](LICENSE).
