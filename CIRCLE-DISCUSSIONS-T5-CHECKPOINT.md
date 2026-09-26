# Circle Object/Page Discussions — Tackle 5 Checkpoint

## Scope

This tackle introduces Circle-scoped conversation threads anchored to a shared `CircleBook` and, optionally, a page number.

- A **community annotation** remains an individual interpretation/quote.
- A **discussion** is a conversation with replies and collective interpretation.
- Whole-book discussions leave `page_number` null.
- Page discussions store a positive page number.
- All discussion/reply operations require active Circle membership.
- Authors may edit or soft-delete their own thread/replies.
- Deleted content is excluded from normal reads.
- Discussion data does not write to `Book`, `ArchivalObject`, archival metadata, provenance, rights, or preservation events.
- The existing Circle boundary is enforced on both the thread and reply records.

## API

- `GET /circles/{circle_id}/discussions/`
- `POST /circles/{circle_id}/discussions/`
- `GET /circles/{circle_id}/discussions/{discussion_id}`
- `PATCH /circles/{circle_id}/discussions/{discussion_id}`
- `DELETE /circles/{circle_id}/discussions/{discussion_id}`
- `POST /circles/{circle_id}/discussions/{discussion_id}/replies`
- `PATCH /circles/{circle_id}/discussions/{discussion_id}/replies/{reply_id}`
- `DELETE /circles/{circle_id}/discussions/{discussion_id}/replies/{reply_id}`

## Migration

`b5c6d7e8f9a0_add_circle_discussions.py`

Down revision: `a4b5c6d7e8f9`

## Native

- Circle detail shows discussion counts and recent threads.
- Members can start a whole-book or page discussion.
- Dedicated thread screen displays the conversation and replies.
- Members can reply, edit/delete their own replies, and edit/delete their own discussion.
- The UI explicitly distinguishes community conversation from archival authority.

## Validation

- `python -m compileall -q app` passes.
- `alembic heads` reports one head: `b5c6d7e8f9a0`.
- Native TypeScript was not run because this review checkpoint intentionally does not include `node_modules`.
- Full FastAPI runtime/import verification remains blocked in this isolated checkpoint by the existing environment's MySQL/PyMySQL dependency mismatch; this is not presented as a passed integration test.
