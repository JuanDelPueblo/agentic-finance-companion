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
