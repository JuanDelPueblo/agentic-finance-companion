# Setup

## Run in containers

With Docker Compose or Podman Compose installed, run from the repository root.

```sh
docker compose up --build -d   # or: podman compose up --build -d
```

Open [localhost:5173](http://localhost:5173). The page reads **Backend: ok** when the
API can reach PostgreSQL. The API reference is at [localhost:8000/docs](http://localhost:8000/docs).
The worker starts alongside the API and waits for shutdown.

Stop the stack with `docker compose down` or `podman compose down`.

## Run on the host

To run the API and frontend on the host, install [uv](https://docs.astral.sh/uv/)
and Node.js 24. Start PostgreSQL from the repository root.

```sh
docker compose up -d db   # or: podman compose up -d db
cd backend
uv sync --locked
uv run uvicorn app.main:app --reload
```

In a second terminal, start the frontend from the repository root.

```sh
cd frontend
npm ci
npm run dev
```

## Local settings

Copy `.env.example` to `.env` if you want to override the PostgreSQL defaults.
Compose builds the container connection URL from the `POSTGRES_*` settings.
When running the API on the host, update `DATABASE_URL` to match any changes to
the database credentials or published port.

## Plaid Sandbox

The Plaid Sandbox is Plaid's test environment with fake banks. Follow these steps to
load Sandbox accounts and transactions into your local database without a frontend.

You need Plaid Sandbox keys from the
[Plaid dashboard](https://dashboard.plaid.com/developers/keys).

1. Copy `.env.example` to `.env` if you don't have a `.env` yet.
2. In `.env`, set `PLAID_CLIENT_ID` and `PLAID_SANDBOX_SECRET` to your Sandbox keys.
3. Generate an encryption key with the command in `.env.example`, and set
   `TOKEN_ENCRYPTION_KEY` to it.
4. Start PostgreSQL from the repository root:

    ```sh
    docker compose up -d --wait db   # or: podman compose up -d --wait db
    ```

5. Create the tables. From `backend/`, run:

    ```sh
    uv run alembic upgrade head
    ```

6. Link a Sandbox bank:

    ```sh
    uv run python scripts/plaid_sandbox_link.py
    ```

    The script prints `Linked First Platypus Bank as item <id> with <n> transactions.`
    The accounts and transactions are now in PostgreSQL, under a local test user.

## Plaid endpoints

Plaid Link is the window where a user signs in to their bank. The frontend opens it with
a link token, and the backend then saves the bank connection.

| Endpoint | What it does |
|---|---|
| `POST /api/plaid/link-token` | Creates a link token. To reconnect a broken bank connection, send its `item_id`. |
| `POST /api/plaid/exchange` | Saves the bank connection from Plaid Link and imports its accounts and transactions. |
| `POST /api/plaid/webhook` | Receives updates from Plaid. Imports new transactions and records connections that need a new sign-in. |
