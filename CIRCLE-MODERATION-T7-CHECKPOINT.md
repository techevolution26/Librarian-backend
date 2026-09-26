# The Librarian — Sprint 3 Tackle 7: Circle Moderation Checkpoint

## Scope

Moderation governs community content inside a Circle. It does not alter archival truth.

Community content covered:

- Circle annotations
- Circle discussion threads
- Circle discussion replies

## Moderation model

`CircleModerationReport` stores:

- Circle
- reporter
- target type and target ID
- reason
- optional details
- open/resolved status
- reviewer
- review timestamp
- moderation action
- action note
- creation/update timestamps

Supported reasons:

- harassment
- hate
- spam
- privacy
- copyright
- other

Supported actions:

- dismiss
- hide

A hidden community item uses the existing `deleted_at` soft-delete boundary. The moderation report remains as the audit record.

## Authorization

- Any active Circle member can report community content in that Circle.
- Only Circle owners/admins can review moderation reports.
- A report cannot target content from another Circle.
- Community moderation never grants archival curator authority.
- No moderation endpoint writes to `Book`, `ArchivalObject`, archival metadata, provenance, rights, or preservation events.

## Native flow

Members can report:

- annotations from Circle detail
- discussion threads from the discussion screen
- discussion replies from the discussion screen

Circle owners/admins receive a moderation queue from Circle detail and can:

- dismiss a report
- hide the reported community content

The queue shows the reported content preview and author so moderators can review the actual community material rather than only a numeric target ID.

## Migration

```text
c6d7e8f9a0b1_add_circle_moderation.py
```

Previous head:

```text
b6c7d8e9f0a1
```

Current head:

```text
c6d7e8f9a0b1
```

## Validation

Backend:

```text
python -m compileall -q app
→ passed

alembic heads
→ c6d7e8f9a0b1 (head)
```

Native TypeScript was not claimed as passed because the checkpoint does not include installed `node_modules`; a bare system `tsc` invocation cannot resolve the Expo/React project dependencies and therefore is not a valid project typecheck.

Full FastAPI runtime integration was not claimed because the isolated checkpoint environment has the previously documented database-driver mismatch when importing the complete application.

## Sprint 3 board after Tackle 7

- 🟡 Connections
- 🟡 Circles
- 🟡 External invitations
  - ✅ Tackle 1 — invitation backend foundation
  - ✅ Tackle 2 — preview + acceptance
  - ✅ Tackle 3 — expiry/revocation + management
- ✅ Invitation preview
- ✅ Invitation expiry/revocation
- ✅ Community annotations
- ✅ Object/page discussions
- ✅ Curator vs community authority
- ✅ Moderation

## Architectural boundary

```text
ARCHIVAL RECORD
      │
      └── CURATOR / GLOBAL ADMIN AUTHORITY
                  │
                  └── remains authoritative

COMMUNITY CONTENT
      ├── Annotation
      ├── Discussion
      └── Reply
                  │
                  ↓
             MODERATION
          ├── Report
          ├── Review
          ├── Dismiss
          └── Hide community content
```

This completes the current Sprint 3 Living Archive moderation layer. Sprint 4 can begin only after the T7 checkpoint has been reviewed.
