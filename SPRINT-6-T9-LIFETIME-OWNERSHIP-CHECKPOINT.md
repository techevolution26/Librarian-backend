# Sprint 6 T9 — Lifetime Ownership Integration

## Architecture

```text
Verified Purchase
      ↓
CreatorLifetimeAccess
      ↓
Lifetime-access Entitlement
      ↓
Book Access
```

A Purchase remains the transaction/payment record. `CreatorLifetimeAccess` is the durable ownership relationship. `Entitlement` remains the access authority.

## Changes

- Added nullable `purchase_id` to `CreatorLifetimeAccess`.
- Added a unique purchase reference and index.
- Added `grant_lifetime_access_from_purchase()` service.
- Added `revoke_lifetime_access_for_purchase()` service.
- Verified purchase fulfillment now materializes durable lifetime ownership.
- Ownership creates the corresponding `source="lifetime_access"` book entitlement.
- Purchase refunds revoke the ownership-derived entitlement and lifetime ownership.
- Admin/manual lifetime grants explicitly clear purchase linkage.
- Admin API cannot fabricate `access_source="purchase"`; purchase ownership is created only by verified purchase fulfillment.
- Added purchase reference to lifetime-access API schema/read responses.
- Creator revenue ledger, payout records, subscription records, and purchase transaction state remain separate.

## Migration

Revision: `b7c8d9e0f1a2`
Previous: `a6b7c8d9e0f1`

## Validation

- `python3 -m compileall -q app tests`: PASS
- Focused Sprint 6 regression suite: **56 passed**
- Alembic head: `b7c8d9e0f1a2`
- Migration revision IDs: unique
- Full FastAPI startup: not claimed in this isolated environment because the existing `passlib` runtime dependency is unavailable there.
