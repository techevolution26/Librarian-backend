# The Librarian — Sprint 6 T3 Feature Limits Checkpoint

## Status

- Sprint 6 T1 — Entitlement Engine: complete
- Sprint 6 T2 — Plans: complete
- **Sprint 6 T3 — Feature Limits: complete**

## Scope

T3 defines feature/capability limits as **subscription-plan catalogue metadata**.

It does **not** implement:

- customer subscriptions
- billing or payment processing
- purchase records
- user-to-plan assignment
- entitlement creation
- usage metering
- bookmark enforcement
- notebook enforcement

Those concerns remain in later Sprint 6 tackles.

## Architecture

```text
SubscriptionPlan
       ↓
SubscriptionPlanFeatureLimit
       ↓
Feature configuration
       ↓
Future subscription / entitlement resolution
       ↓
Future usage enforcement
```

A feature configuration supports:

- `enabled=false` — feature is unavailable on the plan
- `enabled=true` + numeric `limit_value` — feature has a finite ceiling
- `enabled=true` + `limit_value=null` — feature is explicitly unlimited

The model does not grant a user access by itself.

## Backend changes

### Model

Added `SubscriptionPlanFeatureLimit`:

- `plan_id`
- `feature_key`
- `enabled`
- `limit_value`
- timestamps
- unique `(plan_id, feature_key)` constraint
- foreign-key cascade from plan
- non-negative numeric limit constraint

### Plan API

`SubscriptionPlanRead` now includes `feature_limits`.

Therefore public active-plan catalogue responses can describe what each plan permits without representing a customer subscription.

### Admin API

Added:

- `PUT /plans/admin/{plan_id}/features/{feature_key}`
- `DELETE /plans/admin/{plan_id}/features/{feature_key}`

Only administrators can mutate feature configurations.

### Service

Added `get_plan_feature_limit()` for normalized plan-level feature resolution.

This service intentionally does not resolve a user's subscription or entitlement.

### Migration

Added:

`c9d0e1f2a3b4_add_subscription_plan_feature_limits.py`

Down revision:

`f5a6b7c8d9e0`

The repository contains 29 migration revisions with no duplicate revision IDs.

## Validation

- Focused Sprint 6 regression suite: **24 passed**
- `python3 -m compileall -q app tests`: **PASS**
- `alembic heads`: **c9d0e1f2a3b4 (head)**
- Migration revision uniqueness: **29 revisions, 0 duplicates**
- SQLite persistence/service integration: **PASS**
- Plan → feature-limit schema integration: **PASS**
- ZIP integrity: **PASS**

Full FastAPI application import/startup was not claimed because the isolated checkpoint runtime is missing the existing `passlib` dependency.

Historical full-migration SQLite execution was not claimed because older repository migrations contain PostgreSQL-specific operations; the T3 migration itself uses standard SQLAlchemy/Alembic operations.

## Deliberately deferred

- T4 Bookmark Limits
- T5 Notebook Limits
- T6 Advanced Reader Capabilities
- T7 Subscription Billing
- T8 Purchase Entitlements
- T9 Lifetime Ownership Integration
- T10 Institutional Plans
