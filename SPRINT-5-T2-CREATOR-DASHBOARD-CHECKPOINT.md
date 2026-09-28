# Sprint 5 T2 — Creator Dashboard Checkpoint

## Scope

T2 establishes the creator dashboard on top of the existing `CreatorAccount` identity. It does not create a second creator identity model and does not invent book, sales, revenue, analytics, or entitlement data before their underlying Sprint 5 models exist.

## Backend

- `GET /creator/dashboard`
- dashboard response includes:
  - creator account
  - profile completion percentage
  - profile-complete flag
  - missing available profile fields
- profile completeness is derived from the existing CreatorAccount fields only.
- pure dashboard aggregation lives in `app/services/creator.py` so it can be tested without importing the full route/auth stack.
- no database migration required.

## Native

- new `app/creator-dashboard.tsx`
- authenticated profile now opens the Creator Dashboard.
- existing `app/creator.tsx` remains the create/edit CreatorAccount screen.
- dashboard handles missing creator accounts with a creation CTA.
- dashboard shows creator status, public visibility, profile readiness, and the next publishing layer without pretending book submission is implemented.

## Validation

- `python -m compileall -q app tests/test_creator_dashboard.py` — PASS
- isolated SQLite targeted tests — **11 passed**:
  - `tests/test_creator_account.py`
  - `tests/test_creator_dashboard.py`
  - `tests/test_archival_ocr.py`
  - `tests/test_iiif_image.py`
- `alembic heads` — PASS: `e3f4a5b6c7d8 (head)`
- native source regression checks — PASS
- full native TypeScript check is not claimed because the checkpoint intentionally excludes `node_modules` and dependencies were not available in this environment.
- full application runtime against the project database is not claimed.
