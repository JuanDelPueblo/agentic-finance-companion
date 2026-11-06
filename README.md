# Agentic Finance Companion

A web app that turns bank data and a few questions into a financial plan for students and
early-career adults with irregular income. A deterministic engine computes the numbers, an
LLM writes the plan, and a validator checks the plan before the user sees it.

Capstone project, University of Puerto Rico at Mayagüez, Fall 2026.

## Team

| Member | GitHub | Area |
|---|---|---|
| Edyan A. Cruz Vélez | [JuanDelPueblo](https://github.com/JuanDelPueblo) | Infrastructure and integrations |
| Julio Camacho | [CdoxHype](https://github.com/CdoxHype) | Backend and planning engine |
| Ángel A. Martínez Maldonado | [AngelMartinez33](https://github.com/AngelMartinez33) | Frontend and user experience |

## Quick start

You need Podman or Docker with Compose, `make`, [uv](https://docs.astral.sh/uv/), and
Node.js 24.

```sh
make setup                     # create .env and install dependencies
podman compose up --build -d   # or: docker compose up --build -d
```

Open [localhost:5173](http://localhost:5173). All external services run as mocks until
you add credentials to `.env`.

## Documentation

See [the documentation site](https://juandelpueblo.github.io/agentic-finance-companion/),
or read it in [`docs/`](docs/): [Overview](docs/index.md), [Setup](docs/setup.md), and
[Development](docs/development.md).
