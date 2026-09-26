# Tackle 6 — Curator vs Community Authority

## Authority boundary

The Librarian now distinguishes community participation from explicit archival authority.

```text
ARCHIVAL OBJECT
   ├── archival metadata / provenance / rights
   └── explicit curator_user_id

CIRCLE MEMBER
   ├── annotations
   └── discussions / replies

COMMUNITY ACTIVITY ──X──> archival record mutation

ADMIN
   └── global archival authority + curator delegation

ASSIGNED CURATOR
   └── authority over the assigned archival object
```

## Backend

- Added nullable `archival_objects.curator_user_id` with `SET NULL` deletion behavior.
- Added `require_archival_curator(...)`.
- Global `ADMIN` retains archival authority.
- An explicitly assigned active user can update/archive the assigned archival object.
- Only a global `ADMIN` can assign or clear an object's curator.
- Curator assignment is not editable through the general archival update payload, preventing an assigned curator from delegating their own authority.
- Community annotation/discussion routes remain Circle-member scoped and do not call archival mutation services.
- Added `PATCH /archival-objects/admin/{object_id}/curator`.
- Existing public archival reads remain unchanged.

## Native

The discussion screen and Circle detail explicitly communicate that community discussion/interpretation does not modify the archive record. No new dependency was introduced.

## Validation

- `python -m compileall -q app` passed.
- `alembic heads` reports `b6c7d8e9f0a1 (head)`.
- Full FastAPI runtime import/integration testing remains unavailable in the isolated checkpoint environment because its configured database driver does not match the installed dependencies.
- Native TypeScript was not claimed as passed because the checkpoint does not include `node_modules`.
