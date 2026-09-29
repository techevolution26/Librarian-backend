# Sprint 6 T4 — Bookmark Limits Checkpoint

## Status

Complete.

## Scope

T4 applies the Sprint 6 feature-limit foundation to bookmarks without inventing subscription ownership or billing.

### Implemented

- Explicit `bookmark_count` feature key.
- Current bookmark usage service scoped to a user.
- Plan-scoped bookmark limit resolver.
- Disabled bookmark feature is treated as unavailable.
- Finite bookmark limits enforce the ceiling in the reusable decision service.
- `limit_value=None` with `enabled=True` represents unlimited bookmarks.
- Missing bookmark policy is **not** treated as unlimited.
- `GET /bookmarks/usage` exposes current bookmark count without assuming a user's plan.

## Boundary

T4 does **not** create a user subscription or assign a plan to a user. Therefore the reusable limit decision accepts an explicit `plan_id`; it does not guess which plan a user owns.

Subscription ownership and the authoritative effective-plan resolver remain future work in T7. Once that exists, the bookmark creation path can consume this same decision without changing the limit model.

T5 will apply the same architecture to notebook limits.

## Validation

- Dedicated bookmark-limit tests: 8 passed.
- Existing T2/T3 feature-limit tests remain covered by the Sprint 6 suite.
- Python compileall: pass.
- Alembic head remains `f5a6b7c8d9e0` because T4 requires no schema migration.
- ZIP integrity: pass.
- Full FastAPI startup is not claimed because the isolated checkpoint environment retains the existing missing `passlib` dependency limitation.
