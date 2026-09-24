# Reader Intelligence — Highlight → Notebook Note

This checkpoint adds a backend-owned, idempotent conversion from a saved personal highlight into a private Notebook note.

## Endpoint

`POST /highlights/{highlight_id}/develop`

Returns the user's `Note`.

## Behavior

- Requires ownership of the highlight.
- If the highlight already references a valid note owned by the user, returns that note.
- Otherwise creates a Notebook note with the highlight's `book_id`, `page_number`, and selected passage.
- Links the highlight to the new note through the existing `highlight.note_id` field.
- Does not alter archival metadata.
- No database migration is required because the existing Highlight → Note foreign key already supports this relationship.
