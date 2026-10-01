# The Librarian — Backend Development

## Local development

Use PostgreSQL for normal development. DBeaver can connect using the same database host, port, database, username, and password configured for the development environment.

Typical Docker workflow:

```bash
docker compose up -d --build
```

Run backend checks from the project environment:

```bash
python3 -m compileall -q app tests
pytest -q
alembic heads
```

Focused tests are preferred while implementing a tackle, followed by the broader regression suite.

## Environment

The backend requires its configured `DATABASE_URL` and `SECRET_KEY`. Test commands should supply explicit test values when the local environment does not provide them.

Do not claim full application startup if the validation environment is missing an existing runtime dependency such as `passlib`.

## Migrations

Every schema change requires an Alembic migration. Revision IDs must remain unique and the project should have a single current head.

Do not silently reuse an existing revision identifier. Several historical tackles exposed why explicit collision checks matter.

## API design

- Keep request/response schemas explicit.
- Keep authorization in services/routes, not only in the native client.
- Preserve idempotency for webhook/provider events.
- Use immutable records where the domain requires an audit trail.
- Avoid adding a new model when an existing authoritative model already represents the concept.
- Do not invent provider objects, prices, sales, revenue, or access state.

## Storage safety

Public file delivery must pass through the same authorization boundary as the API access decision. Do not expose protected assets through an unguarded static mount.

## Documentation hygiene

All project markdown documentation belongs under `docs/`. The documentation set is intentionally consolidated. Do not recreate one markdown file for every tackle.
