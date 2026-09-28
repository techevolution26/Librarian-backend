# Sprint 5 T7 — Lifetime Access

## Scope

T7 establishes durable lifetime ownership independently from payment processing.

## Backend

- Added `CreatorLifetimeAccess` scoped to `(user_id, hosted_book_id)`.
- Explicit `active` / `revoked` lifecycle.
- Optional `paid_offer_id` preserves commercial provenance without equating payment with ownership.
- Controlled admin grant/revoke endpoints provide a fulfillment seam for later payment integration.
- User endpoints expose only the current user's active lifetime ownership.
- Hosted books must be in the hosted state before access can be granted.
- Migration: `d9e0f1a2b3c4`.

## Native

- Added lifetime-access API types/functions.
- Added `app/lifetime-access.tsx` for the user's durable ownership list.
- Added a Creator Dashboard entry point.

## Explicitly not included

- Checkout/payment processing
- Stripe transaction records
- subscription entitlements
- revenue accounting
- payouts
- automatic purchase fulfillment

## Validation

- 20 targeted creator tests passed.
- Backend compileall passed.
- Alembic has one head: `d9e0f1a2b3c4`.
- Native deterministic source checks passed.
- Full native TypeScript was not claimed because `node_modules` is excluded from the checkpoint.
