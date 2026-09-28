# Sprint 5 T6 — Paid Books Checkpoint

Status: COMPLETE

This tackle establishes the creator-side commercial offer/catalog boundary for hosted books.

## Implemented
- `CreatorPaidBook` model, one offer per hosted book.
- Price stored as integer minor currency units.
- Three-letter normalized currency code.
- Offer lifecycle: `draft`, `active`, `archived`.
- Active offer requires a hosted file and an active rights declaration allowing commercial use.
- Archived offers cannot be repriced.
- Creator ownership and suspended-account protections.
- Native creator hosted-book screen can create, activate, draft, and reprice a paid offer.

## Explicitly not implemented
- Checkout/payment processing.
- Stripe Product/Price creation.
- Purchases or payment records.
- User entitlements or lifetime ownership.
- Revenue accounting.
- Creator payouts.
- Public publication of the book.

Those boundaries belong to later Creator Economy / Subscription tackles.

## Validation
- `python -m compileall -q app tests` — PASS
- Targeted creator suite — **17 passed**
- `alembic heads` — **c8d9e0f1a2b3 (head)**
- Native deterministic source regression — PASS
- ZIP integrity — PASS
- Native full TypeScript — not claimed; checkpoint excludes `node_modules`.
- Full production runtime — not claimed; isolated environment does not contain the project's configured MySQL driver.
