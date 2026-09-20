# The Librarian — FastAPI backend

FastAPI service for The Librarian digital archive and reading community.

## Local Docker development

1. Copy `.env.example` to `.env`.
2. Replace `SECRET_KEY` with a random development secret.
3. Start the stack with Compose Watch:

```bash
docker compose up --watch
```

The API is available at `http://localhost:8000` and PostgreSQL at `localhost:5432`.

Compose Watch syncs `app/` into the API container and rebuilds when
`requirements.txt` or `Dockerfile` changes. It requires Docker Compose 2.22+.

Migrations run automatically when the API container starts.

## Database

PostgreSQL is the primary database. The application uses SQLAlchemy and Alembic
with the `postgresql+psycopg://` driver.

## Production storage

Uploaded PDFs, covers, and avatars must use persistent storage. On Railway,
attach a Volume at `/app/storage` for a simple single-instance deployment, or
move uploads to an S3-compatible storage bucket before running multiple API
replicas.

## Secrets

Never commit `.env`, database credentials, or JWT secrets. Generate a new
`SECRET_KEY` for each environment.


### Realtime notifications

The API now persists in-app notifications and delivers new events over a WebSocket. The Expo client subscribes when authenticated, keeps the bell badge live, and polls every 15 seconds as a resilience fallback.
