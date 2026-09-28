# Sprint 5 T9 — Revenue Accounting Checkpoint

## Scope

Introduces a provider-neutral, immutable creator revenue ledger. This tackle does **not** execute payments, create Stripe objects, grant lifetime access, or process payouts.

## Backend

- `CreatorRevenueLedgerEntry` is immutable by API design.
- Verified commercial events are recorded through `record_verified_revenue_event`.
- Provider + provider event ID is unique for idempotency.
- Gross amount, creator share, and platform share must balance exactly.
- Currency must match the paid offer.
- Sales require an active paid offer and hosted book.
- Reversals/adjustments are compensating ledger entries; original entries are never mutated.
- Creator revenue summary endpoint: `GET /creator/revenue/summary`.
- Controlled admin recording seam: `POST /creator/revenue/admin/record`.
- Migration: `e2f3a4b5c6d7`, single Alembic head.
- Resolved an existing T8-tree revision collision by assigning the new T9 migration the unique revision ID `e2f3a4b5c6d7`.

## Native

- Added creator revenue summary API contract.
- Creator dashboard now shows recorded commercial activity separately from reader analytics.
- No payment UI, checkout UI, payout UI, or fabricated earnings.

## Validation

- T9 + creator regression suite: **30 passed**.
- `python -m compileall -q app tests`: passed.
- `alembic heads`: `e2f3a4b5c6d7 (head)`.
- Native T9 source-contract checks: passed.
- ZIP integrity: passed.
- Full FastAPI import/startup not claimed: isolated environment lacks the existing `passlib` dependency.
- Full native TypeScript not claimed: checkpoint excludes `node_modules`.
