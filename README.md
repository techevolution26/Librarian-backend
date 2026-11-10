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

## Digital archive ingestion

Admin ingestion is draft-first. A PDF upload creates a catalog record and a versioned `BookAsset`; cover uploads and PDF replacements create additional asset versions without deleting the previous stored object. A separate `PATCH /books/{book_id}/publish` operation moves a valid, active record into the public catalog. Public book/content endpoints only expose published, non-archived records.

The current development storage backend is the mounted local `storage/` volume. The asset model stores stable storage keys, checksums, versions, MIME types, sizes, uploader identity, and current-asset state so the storage implementation can later move to durable object storage without changing the catalog contract.

## Source-native Reader research

Private bookmarks, highlights, Notebook notes, and quote references can attach
to typed source anchors through `/reader/source-anchors`. Locators preserve the
difference between PDF pages/text, IIIF canvases, image regions, Book
transcription spans, verified OCR spans, and media time ranges. Existing
`page_number` fields remain for compatibility and are populated only for PDF
anchors. See `docs/ARCHITECTURE.md`, `docs/DOMAINS.md`, and
`docs/DEVELOPMENT.md` for the source-locator contract.

## Source-anchor validation

See [`docs/READER-HTTP-ACCEPTANCE.md`](docs/READER-HTTP-ACCEPTANCE.md) for the FastAPI HTTP regression flow and production PostgreSQL acceptance boundary.
