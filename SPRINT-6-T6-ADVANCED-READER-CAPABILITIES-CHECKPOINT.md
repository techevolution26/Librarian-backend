# The Librarian — Sprint 6 T6 Checkpoint

## Tackle
Advanced Reader Capabilities

## Status
Complete.

## Scope
T6 defines the plan-catalogue boundary for advanced reader capabilities. It does not create subscriptions, purchases, billing, or user ownership resolution.

## Implemented
- `advanced_reader` is the only currently declared advanced-reader capability.
- `app/services/reader_capabilities.py` provides typed catalogue resolution.
- Active plan lookup is normalized and excludes draft/archived plans.
- Unknown advanced-reader capabilities are rejected rather than silently accepted.
- `GET /reader/capabilities/{plan_code}` exposes active-plan capability metadata.
- Capability discovery remains catalogue metadata and does not imply entitlement.
- Existing bookmark and notebook limits remain separate feature keys.

## Boundary
```text
Subscription Plan
    ↓
Feature Configuration
    ↓
Advanced Reader Capability Catalogue

Future:
User Subscription → Effective Plan → Entitlement / Access Decision
```

## Validation
- 47 focused Sprint 6 tests passed.
- `python -m compileall -q app tests` passed.
- Alembic head remains `c9d0e1f2a3b4`.
- 29 migration revisions present; no duplicate revision IDs.
- No database migration required for T6.
- Full FastAPI startup is not claimed because the isolated checkpoint environment retains the existing missing `passlib` dependency limitation.
- Full native TypeScript is not applicable; T6 is backend-only.
