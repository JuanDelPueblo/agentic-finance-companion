# Setup

## Prerequisites

- Podman with `podman compose`, or Docker with Compose
- `make`
- [uv](https://docs.astral.sh/uv/) and Node.js 24

The commands below use `podman compose`. With Docker, use `docker compose`.

## Run in containers

```sh
make setup                     # create .env and install dependencies
podman compose up --build -d
```

Open [localhost:5173](http://localhost:5173). The page reads **Backend: ok**. The API
reference is at [localhost:8000/docs](http://localhost:8000/docs).

Code changes reload automatically. Stop the stack with `podman compose down`. Add `-v`
to also delete the database.

## Run on the host

```sh
podman compose up -d db

cd backend
uv run uvicorn app.main:app --reload

cd frontend        # in a second terminal
npm run dev
```

## Settings

`.env.example` lists every setting with a comment. By default, all external services are
mocks:

- **Auth:** requests without a token act as `dev-user`. Send
  `Authorization: Bearer dev:<name>` to act as another user.
- **Plaid:** any public token that starts with `public-mock-` connects three synthetic
  accounts. `public-mock-login-required` gives a connection that needs re-linking.
- **LLM:** returns only the responses that a test registers with
  `MockLLM(responses=...)`.

To use the Plaid Sandbox, put your Sandbox keys in `.env` and set `PLAID_PROVIDER=plaid`.

## Make targets

| Command | What it does |
|---|---|
| `make setup` | Creates `.env` and installs dependencies |
| `make lint` | Lints and type-checks both apps |
| `make test` | Runs the unit tests |
| `make openapi` | Regenerates the API contract and frontend types |
| `make docs` | Builds this site |
| `make check` | Runs everything CI runs |
