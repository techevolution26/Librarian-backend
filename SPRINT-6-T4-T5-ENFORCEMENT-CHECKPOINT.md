# The Librarian — Sprint 6 T4/T5 Enforcement Checkpoint

## Scope

Closes the creation-boundary enforcement gaps for bookmark and private notebook-note limits.

## T4 — Bookmark Limits
- `POST /bookmarks/` now resolves the user’s effective active subscription.
- If an effective subscription exists, the configured `bookmark_count` policy is enforced before insert.
- Finite limits block at the ceiling.
- Disabled policies block creation.
- Explicit unlimited policies (`enabled=true`, `limit_value=null`) allow creation.
- Users without an effective subscription are not assigned an invented default plan; creation remains outside plan-specific enforcement until a default/free-plan policy is explicitly defined.
- Per-user row locking is used during creation to serialize concurrent finite-limit checks on PostgreSQL.

## T5 — Notebook Limits
- `POST /notebook/notes` now resolves the user’s effective active subscription.
- If an effective subscription exists, the configured `notebook_note_count` policy is enforced before insert.
- Finite limits block at the ceiling.
- Disabled policies block creation.
- Explicit unlimited policies allow creation.
- No default plan is invented for users without an effective subscription.
- Per-user row locking protects concurrent creation checks.

## Error contract
Limit violations return HTTP 403 with a structured detail payload containing `code`, `message`, `count`, and `limit`.

## Validation
- Focused Sprint 6 regression suite: 64 passed.
- `python3 -m compileall -q app tests`: PASS.
- Alembic head remains the Sprint 6 T9 head.
- No migration was required.
- No native changes.
- Full FastAPI startup is not claimed because the isolated validation environment lacks the existing `passlib` runtime dependency; the project requirements already declare it.
