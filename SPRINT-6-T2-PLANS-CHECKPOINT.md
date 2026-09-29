# Sprint 6 — T2 Plans Checkpoint

Status: COMPLETE

## Scope

T2 establishes the subscription plan catalogue only. It does not create customer subscriptions, purchases, invoices, payment records, Stripe objects, or entitlement mutations.

## Backend

Added `SubscriptionPlan` with:

- stable unique `code`
- display `name` and `description`
- price in integer minor units
- three-letter currency code
- billing interval: `none`, `month`, `year`
- lifecycle: `draft`, `active`, `archived`
- explicit display ordering
- timestamps

Added public catalogue endpoints:

- `GET /plans`
- `GET /plans/{code}`

Added admin catalogue management:

- `GET /plans/admin/all`
- `POST /plans/admin`
- `PATCH /plans/admin/{plan_id}`

Plan validation prevents zero-price plans from carrying a recurring interval and prevents paid plans from using `none`.

Feature limits are deliberately deferred to Sprint 6 T3.

## Migration

Revision: `f5a6b7c8d9e0`

Previous: `a5b6c7d8e9f0`

Alembic reports one head: `f5a6b7c8d9e0`.

## Validation

- `python -m compileall -q app tests` — PASS
- focused T2/T1/lifetime suite — **16 passed**
- dedicated T2 suite — **8 passed**
- Alembic heads — single head `f5a6b7c8d9e0`
- migration revision IDs checked for uniqueness
- temporary SQLite test database removed after validation

The complete historical migration chain was not claimed as SQLite-clean because the project already contains older PostgreSQL-specific migration operations. T2 itself uses standard table/index/check-constraint operations.

## Architectural boundary

```text
Subscription Plan
       ↓
Future Subscription / Purchase
       ↓
Entitlement
       ↓
Access Decision
```

T2 stops at the plan catalogue. Billing and subscription state belong to later tackles.
