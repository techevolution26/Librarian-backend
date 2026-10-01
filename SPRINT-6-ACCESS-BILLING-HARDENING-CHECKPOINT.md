# Sprint 6 — Access & Billing Hardening Checkpoint

## Status
- Backend access enforcement hardened
- Native access UX hardened
- No database migration required

## Backend changes
- Paid creator books with an active hosted paid offer are no longer treated as public book access.
- `resolve_book_access()` is now authoritative for paid-book access.
- `/books/{book_id}/content` now enforces the access decision.
- `start_reading` now enforces the access decision.
- Book PDF delivery moved behind an access-aware file route.
- Existing `/static/books/{filename}` URLs remain supported through the protected compatibility route.
- Newly uploaded PDFs use `/books/file/{filename}`.
- Optional authentication was added so genuinely free published books remain readable without credentials.
- Existing bookmark/note limits and institutional/direct subscription resolution remain unchanged.

## Native changes
- `ApiError` now surfaces structured backend `detail.message` values.
- Book Detail disables reading when the backend reports access is required.
- Reader distinguishes authentication failure, access denial, and generic reader failure.

## Validation
- `python3 -m compileall -q app tests`: PASS
- Focused Sprint 6 regression suite: 44 passed
- Alembic head: `d1e2f3a4b5c6`
- Migration revision IDs: 33 total, no duplicates
- Native full TypeScript check: NOT CLAIMED because checkpoint intentionally excludes `node_modules`.
- Full FastAPI startup: NOT CLAIMED because the isolated validation environment lacks the existing `passlib` dependency.

## Architectural boundary
Subscription plans, subscriptions, institutional plans, purchases, lifetime ownership, revenue accounting, payouts, and entitlements remain distinct domains. This hardening only strengthens the access boundary between those domains and actual book reading.
