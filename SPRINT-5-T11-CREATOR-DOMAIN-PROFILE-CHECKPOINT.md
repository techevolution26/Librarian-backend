# Sprint 5 T11 — Creator Domain/Profile Checkpoint

## Status

- Sprint 5 T11 — **Creator Domain/Profile**: complete
- Sprint 5 is now complete through T11.

## Architecture

```text
CreatorAccount.slug
      ↓
Canonical public creator path: /creator/{slug}
      ↓
Public creator API: /creator/public/{slug}
      ↓
Public identity
      ↓
Only hosted + published + non-archived catalog books
```

## Backend

Added a public creator profile contract without introducing another identity table or migration.

- `CreatorPublicProfileRead`
- `CreatorPublicBookRead`
- unauthenticated `GET /creator/public/{slug}`
- authenticated `GET /creator/me/public-url`
- public profiles require:
  - `is_public = true`
  - `status = active`
- unavailable/private/suspended profiles return `404`
- books require:
  - creator-hosted status `hosted`
  - catalog visibility `published`
  - `archived_at IS NULL`
- public response deliberately excludes creator `user_id`, account status, payout data, revenue data, rights declarations, submissions, and private hosting metadata
- no new migration; existing unique creator slug is the canonical identity key

## Native

Added:

- `app/creator/[slug].tsx`
- public creator identity/profile presentation
- profile image or initial fallback
- public bio and website
- published-book list
- navigation from creator profile to public book detail
- creator dashboard → **View public profile**
- API types and calls for public profile/canonical public URL

The native route is public and does not require authentication.

## Domain boundary

T11 establishes the creator's canonical **profile path/domain surface**. It does not claim custom DNS/domain ownership or introduce domain verification, routing certificates, or external DNS configuration. Those would be a separate infrastructure capability.

## Validation

- backend `compileall`: **PASS**
- Alembic heads: **single head `f3a4b5c6d7e8`**
- backend T11 contract checks: **PASS**
- native T11 contract checks: **PASS**
- full backend pytest could not be collected in the isolated checkpoint environment because the existing environment is missing `passlib`; network access was unavailable to install it
- no native full TypeScript claim because the checkpoint excludes `node_modules`
- no runtime/startup claim beyond the checks above
