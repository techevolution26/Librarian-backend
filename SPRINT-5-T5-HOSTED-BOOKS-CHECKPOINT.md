# Sprint 5 T5 — Hosted Books Checkpoint

## Scope

T5 establishes the controlled relationship between a creator submission and a private hosted book file without publishing the work.

### Architecture

```text
CreatorAccount
      ↓
CreatorBookSubmission
      ↓
CreatorRightsDeclaration (hosting_allowed=true)
      ↓
CreatorHostedBook
      ↓
Book (visibility=draft)
      ↓
BookAsset (access, private)
      ↓
AssetStorageLocation (private storage)
      ↓
SHA-256 checksum
```

## Backend

- Added `CreatorHostedBook` as a one-to-one bridge between a creator submission and a draft `Book` identity.
- Added explicit hosted-book statuses: `draft`, `hosted`, `archived`.
- Added creator endpoints:
  - `GET /creator/submissions/{submission_id}/hosted-book`
  - `POST /creator/submissions/{submission_id}/hosted-book`
  - `POST /creator/submissions/{submission_id}/hosted-book/file`
- Hosting requires an active rights declaration with `hosting_allowed=true`.
- Suspended creator accounts cannot create or upload hosted books.
- Uploaded PDFs become versioned `BookAsset` access assets.
- Physical storage is recorded through `AssetStorageLocation`.
- Hosted assets have no public URL and the draft `Book` remains `visibility=draft`.
- Replacing a hosted PDF creates a new asset version and retires the previous current version without deleting its historical asset record.
- SHA-256 is calculated from the stored file and exposed to the creator as an integrity value.
- No `ArchivalRights` record is created automatically.
- No public publication, paid access, entitlement, revenue, or payout logic is introduced.
- Migration: `a2b3c4d5e6f8_add_creator_hosted_books.py`.

## Native

- Added `CreatorHostedBook` API contract and hosted-book API functions.
- Added `app/creator-hosted/[id].tsx`.
- Added a `Host` action to creator submissions.
- Uses the existing Expo 57 native file picker/upload path.
- Shows hosted file name, size, SHA-256, and private-storage state.
- Supports first upload and replacement upload.
- Explicitly tells creators that hosting is not publication.

## Validation

- `python -m compileall -q app tests` — PASS
- Focused creator regression suite — **13 passed**
- `alembic heads` — `a2b3c4d5e6f8 (head)`
- Backend T5 contract checks — PASS
- Native T5 source contract checks — PASS
- Full native TypeScript check — not claimed because this checkpoint intentionally excludes `node_modules`.
- Full production runtime/database integration — not claimed because the isolated environment does not have the project's configured MySQL driver/runtime dependencies.
