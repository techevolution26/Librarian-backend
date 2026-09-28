# Sprint 5 T8 — Creator Analytics Checkpoint

## Scope

Creator analytics now reports only activity already represented by Librarian data models. It does not fabricate sales, revenue, earnings, conversion, impressions, or other unavailable commercial metrics.

## Backend

- `GET /creator/analytics`
- Submission counts by workflow state
- Hosted-book count
- Active paid-offer count
- Active lifetime-owner count
- Reader count derived from `LibraryItem`
- Active readers in the last 30 days derived from `LibraryItem.last_read_at`
- Completed readers derived from `LibraryItem.finished_at`
- Average reader progress derived from `LibraryItem.progress`
- Per-hosted-book analytics with the same observable metrics
- No database migration required

## Native

Creator Dashboard now displays:

- observed readership
- 30-day active readership
- completed readers
- lifetime owners
- hosted books
- active commercial offers
- average reader progress
- submission/review counts
- per-book readership/progress

The dashboard explicitly states that these are observed platform metrics and does not present revenue or invented sales data.

## Validation

- `python -m compileall -q app tests` — PASS
- targeted creator suite — **23 passed**
- `alembic heads` — `d9e0f1a2b3c4 (head)`
- native deterministic T8 contract checks — PASS
- full native TypeScript — NOT CLAIMED; checkpoint excludes `node_modules`
- production DB/runtime integration — NOT CLAIMED
