# Reader source-anchor HTTP acceptance

The mobile client consumes the following backend contracts:

- `POST /reader/source-anchors`
- `GET /reader/source-anchors?book_id={id}`
- `GET /reader/source-anchors/{id}`
- `DELETE /reader/source-anchors/{id}`
- Bookmark, Highlight, Notebook Note, and QuoteReference create/read/update
  routes that accept or return `source_anchor_id`.

`tests/test_reader_source_anchor_http_integration.py` exercises the FastAPI
application through HTTP requests using an isolated SQLite test database. It
checks source anchor create/read/list, private ownership, association with a
Bookmark, Highlight, Note and QuoteReference, highlight-to-note development,
readable canvas citation output, and legacy page-only Bookmark/Highlight
writes. It verifies that a IIIF canvas reference does not populate
`page_number`.

Run the full backend test suite in an environment with the project's declared
requirements installed and test settings configured:

```bash
pytest -q
```

The HTTP integration test uses the actual FastAPI router and Pydantic response
models. Its SQLite database is a test fixture only; production migration and
runtime acceptance must still be executed against the configured PostgreSQL
database after a backup.

The test does not inspect, read, modify, or require the archival `storage/`
directory or PDF files.


## Recorded checkpoint result (2026-11-09)

- Full backend test suite: **151 passed**, including this FastAPI HTTP integration test.
- Python compilation: passed.
- Alembic graph: one head, `e4b7c9d2a601`.
- The isolated test run supplied SQLite and a temporary test-only `passlib` import shim because the execution environment did not have `passlib` installed. This shim is not part of the application or packaged runtime.
- The production PostgreSQL migration has **not** been executed in this environment. Back up the configured database and run the migration procedure in `docs/READER-ACCEPTANCE.md` before deployment.
