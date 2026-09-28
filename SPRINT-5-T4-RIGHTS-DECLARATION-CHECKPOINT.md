# Sprint 5 T4 — Rights Declaration Checkpoint

## Implemented

- Added immutable, versioned `CreatorRightsDeclaration` records tied to `CreatorBookSubmission`.
- Explicit rights basis vocabulary:
  - original author
  - copyright holder
  - authorized representative
  - licensed
  - public domain
  - other
- Explicit permission scope for hosting, public display, download, redistribution, commercial use, and derivative use.
- Recorded rights holder, rights statement, territory, license information, declaration note, declaring user, timestamp, and generated attestation text.
- Creating a new declaration supersedes the previous active declaration without editing or deleting historical declarations.
- Creator ownership is enforced through the existing CreatorAccount boundary.
- Submission can only enter `submitted` from draft/changes-requested when an active rights declaration exists.
- Native rights declaration screen added and linked from creator submissions.

## Validation

- `python -m compileall -q app tests` — PASS
- Targeted creator tests — `10 passed`
- `alembic heads` — `a1b2c3d4e5f7 (head)`
- Native deterministic regression checks — PASS
- Native TypeScript — not run because `node_modules` is not included in the checkpoint.
- Full production DB/runtime integration — not claimed.

## Boundary

T4 does not create archival `ArchivalRights` records and does not publish or host a Book. Creator rights declarations are a pre-publication creator assertion. Later authorized workflows may use this information when deciding whether a submission can progress into hosting/publication.
