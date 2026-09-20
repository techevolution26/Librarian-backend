# Librarian backend development workflow

## PostgreSQL / DBeaver

Docker publishes PostgreSQL to the host, so DBeaver connects directly to the database rather than through the API.

| DBeaver field | Value |
|---|---|
| Driver | PostgreSQL |
| Host | `localhost` |
| Port | `5432` |
| Database | `librarian` |
| Username | `librarian` |
| Password | value of `POSTGRES_PASSWORD` in `.env` |
| SSL | disabled for local development |

The API uses a different hostname internally:

`postgresql+psycopg://librarian:<password>@db:5432/librarian`

Do not put `localhost` in `DATABASE_URL` inside the API container: `localhost` would mean the API container itself.

## Start

```bash
cp .env.example .env
# replace SECRET_KEY with a long random development secret

docker compose up --build
```

For file-watch development:

```bash
docker compose up --watch
```

Compose Watch now uses `sync+restart` for `app/`. Uvicorn does **not** use `--reload` at the same time. This gives one reload mechanism instead of Compose Watch + Uvicorn WatchFiles both reacting to the same file sync.

## Seed a realistic development dataset

```bash
docker compose exec api python -m app.scripts.seed_db
```

The seed is idempotent and does not drop tables. It creates or updates:

- 6 deterministic demo users
- the complete book seed
- featured content
- onboarding/preferences
- saved / reading / finished library states
- reading progress and bookmarks
- accepted, pending and declined connections
- private and public circles
- circle membership
- circle reading plans
- circle progress updates
- admin activity records
- seeded unread/read notification inboxes
- realtime notification WebSocket testing state

### Demo accounts

All demo accounts use:

`LibrarianDev!2026`

| Role | Email |
|---|---|
| Admin | `admin@librarian.local` |
| Reader | `reader@librarian.local` |
| User | `grace@librarian.local` |
| User | `daniel@librarian.local` |
| User | `amina@librarian.local` |
| User | `samuel@librarian.local` |

These credentials are for local development only.

## PostgreSQL 18 volume note

The compose file mounts the PostgreSQL 18 parent directory:

```yaml
- librarian_postgres_data:/var/lib/postgresql
```

Do not change this to `/var/lib/postgresql/data` with the PostgreSQL 18 image.

If the old development volume was created with the previous mount and contains no valuable data, remove only the PostgreSQL volume and recreate it. Keep `librarian_storage` if it contains uploaded archive files.

## Realtime notifications

The backend persists in-app notifications in PostgreSQL and exposes:

- `GET /notifications/` — current user's inbox
- `GET /notifications/unread-count` — badge count
- `PATCH /notifications/{id}/read` — mark one read
- `POST /notifications/read-all` — clear the unread state
- `WS /notifications/ws?token=<access-token>` — realtime delivery to the Expo app

Connection requests, connection decisions, and circle invitations create notifications. The WebSocket fan-out is intentionally in-process for local development and single-worker deployments; a multi-instance production deployment should move fan-out to Redis/pub/sub or a managed realtime service.
