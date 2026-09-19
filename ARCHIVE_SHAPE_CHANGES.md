# Archive-shape backend changes

What changed, and why, in this pass:

## New provenance/archival fields on `Book`
`accession_no`, `language`, `subjects` (a second, archive-oriented tag set
alongside `genre`), `origin`, `era`, `original_format`
(`born-digital` / `printed` / `manuscript` / `oral-transcription`),
`rights_statement` (`public-domain` / `cc-by` / `all-rights-reserved` /
`restricted`), `condition_notes`, `curator_note`, `checksum_sha256`,
`digitized_by`, `digitized_at`.

All new columns are nullable or defaulted, so existing rows and existing API
consumers keep working unchanged — this is additive, not breaking.

## New/changed endpoints
- `GET /books/facets` — vocabulary currently in use (genres, subjects,
  languages, eras, formats, rights) for building real filter chips instead of
  a hardcoded genre list.
- `GET /books/discover` — now also accepts `subject`, `language`,
  `original_format`, `era` query params.
- `POST /books/upload-pdf` and `PATCH /books/{id}` — accept the new
  provenance fields as form fields. Accession number is auto-generated
  (`TL-XXXXXXXX`) if not supplied; a SHA-256 checksum of the stored PDF is
  computed on upload and on every PDF replacement.

## Fixed
- `requirements.txt` was missing `passlib`/`bcrypt`, which `app/core/security.py`
  already imports for password hashing — a clean `pip install` would have
  failed before login ever ran. Pinned `passlib[bcrypt]==1.7.4` +
  `bcrypt==4.0.1` (newer bcrypt majors drop the API passlib 1.7.4 expects).
- Removed a stray, unused `from pygments.lexer import default` import in
  `app/models/book.py`.

## Migration
New Alembic revision `a92f1d7c44be_add_book_archival_metadata`, chained after
the existing `c5a1b3990228`. Verified end-to-end (`alembic upgrade head`)
against a throwaway SQLite DB in addition to the target MySQL schema — run it
for real with:

```bash
alembic upgrade head
```

## Verified
`pytest` (9 tests, including new ones for the archival fields/helpers),
`alembic upgrade head`, and a full app boot + `/openapi.json` + `/books/facets`
+ `/books/discover` round-trip via `TestClient` all pass.

## Not touched in this pass
Frontend, mobile — by design, this delivery is backend-only. Next step is the
Expo/React Native project.
