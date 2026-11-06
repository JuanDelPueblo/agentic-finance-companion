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

## Current starter

- The React frontend displays the API and database connection status.
- FastAPI exposes `GET /api/health`, which checks the PostgreSQL connection.
- Compose runs the frontend, API, PostgreSQL, and a worker that waits for shutdown.
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
