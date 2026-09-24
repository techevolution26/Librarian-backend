# Reader Intelligence — Highlight Management Checkpoint

## Added

- `Highlight` personal annotation model.
- User ownership enforcement.
- Book and optional Notebook Note linkage.
- Page number, selected source text, optional selection position, and color.
- CRUD API under `/highlights/`.
- Alembic migration `a1b2c3d4e5f6_add_reader_highlights.py` after Notebook/Notes migration `9c3d4e5f6a77`.
- Notebook mobile Highlights view with delete and return-to-reader/page behavior.

## Boundary

Highlights are personal reader intelligence. They do not modify archival metadata, rights, provenance, or preservation records.

## Validation

`python -m compileall -q app` passes.

Alembic migration is not claimed as applied.
