# Sprint 6 T5 — Notebook Limits Checkpoint

## Status

Completed.

## Scope

T5 applies the Sprint 6 feature-limit foundation to the user's private notebook.
It defines a plan-scoped `notebook_note_count` feature and provides current
notebook-note usage and capacity evaluation without inventing subscription
ownership.

## Implemented

- `app/services/notebook_limits.py`
  - `NOTEBOOK_NOTE_COUNT_FEATURE_KEY`
  - `get_notebook_note_count`
  - `get_notebook_note_limit_for_plan`
  - `notebook_limit_allows_note_creation`
- `GET /notebook/usage`
  - reports the current private notebook note count
  - does not assume a subscription plan
- focused tests in `tests/test_notebook_limits.py`
- existing bookmark, feature-limit, plan, entitlement, and lifetime-access tests retained

## Domain boundaries

- Notebook notes remain private reader data.
- Circle annotations/discussions are not counted as notebook notes.
- Bookmarks are not counted as notebook notes.
- The feature limit is catalogue metadata on a subscription plan.
- T5 does not resolve a user's subscription or effective plan.
- T5 does not process billing, purchases, or entitlements.
- Existing notes are never deleted when a plan limit is reduced.
- Enforcement at note-creation time belongs to the later effective-plan/subscription enforcement layer.

## Validation

- Focused Sprint 6 regression suite: **41 passed**
- `python -m compileall -q app tests`: **PASS**
- Alembic head: **c9d0e1f2a3b4**
- Migration revision uniqueness: **PASS**
- No database migration required for T5.

## Important test note

The initial broad SQLite fixture attempted to create unrelated PostgreSQL-specific
payout constraints (`char_length`). The T5 fixture was corrected to create only
the notebook dependency graph, after which the complete focused suite passed.

## Architecture

```text
Subscription Plan
      ↓
notebook_note_count
      ↓
Current Private Notebook Note Count
      ↓
Future Effective Plan Resolution
      ↓
Future Note-Creation Enforcement
```
