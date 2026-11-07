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

## Source-native Reader anchors

The source-anchor API is mounted at `/reader/source-anchors`:

- `POST /reader/source-anchors` validates and creates an immutable anchor.
- `GET /reader/source-anchors?book_id=…` lists the current user's anchors.
- `GET /reader/source-anchors/{id}` reads one of the current user's anchors.
- `DELETE /reader/source-anchors/{id}` detaches the anchor while preserving
  Reader-record text and legacy page fields.

Request shape:

```json
{
  "book_id": 123,
  "locator": {
    "type": "iiif_canvas",
    "canvas_identifier": "tl:canvas:example"
  }
}
```

The `locator.type` discriminator selects one of `pdf_page`, `pdf_text`,
`iiif_canvas`, `image_region`, `text_span`, `ocr_span`, or `media_time`. See
`app/schemas/reader_source_anchor.py` for exact fields, offset units, and
validation constraints. All offsets are zero-based Unicode code points unless the locator is expressed
as canvas coordinates or media time. PDF text ranges are page-local and tied to
a specific asset version; because the backend does not maintain a canonical
PDF text extraction index, clients must derive those ranges from that exact
rendered PDF version. The server validates the page and asset identity, but
cannot independently verify a PDF text offset against a normalized text layer.

Reader writes accept optional `source_anchor_id` values on bookmarks,
highlights, Notebook notes, and quote references. The server verifies anchor
ownership and Book scope, and resolves `page_number` only for PDF anchors. Do
not convert canvas sequence, IIIF canvas identifiers, or media time to a
legacy page number.

Focused tests:

```bash
pytest -q tests/test_reader_source_anchors.py
```

The test module uses an in-memory SQLite subset of the schema and stubs only
the access-decision boundary; production authorization remains in
`resolve_book_access`.
