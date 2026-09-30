# Sprint 6 T10 — Institutional Plans Checkpoint

## Scope

Adds a provider-neutral institutional access layer without inventing pricing, payment behavior, or Stripe objects.

## Implemented

- `SubscriptionPlan.plan_type`: `individual` or `institutional`
- `SubscriptionPlan.seat_limit`: optional positive ceiling for institutional plans
- `Institution`
- `InstitutionMembership`
- `InstitutionSubscription`
- institution owner/admin/member roles
- active/revoked membership lifecycle
- institutional plan assignment
- plan start/end dates
- active institutional plan resolution for members
- effective plan resolution now falls back from an individual subscription to an active institutional plan
- bookmark and notebook feature-limit enforcement can therefore consume institutional plan features
- seat-limit enforcement at member creation
- owner counts toward the institutional seat limit
- revoked/expired institutional membership or plan does not confer institutional plan access
- public/user routes for institution discovery, effective institutional subscription, membership management, and plan assignment
- admin/manager authorization at institution boundaries

## Deliberate boundaries

- No institutional Stripe customer/subscription objects are created in T10.
- No prices or seat counts are seeded.
- No automatic purchase or book entitlements are created by institutional membership.
- Institutional plan features remain catalogue metadata and are consumed through the existing feature-limit services.
- Direct user subscription takes precedence over institutional subscription when resolving the effective plan.

## Validation

- Focused Sprint 6 regression + T10 suite: 67 passed
- `python3 -m compileall -q app tests`: PASS
- Alembic head: `d1e2f3a4b5c6`
- Migration revision IDs: 33 total, no duplicates
- ZIP integrity: verified
- Full FastAPI startup: not claimed because the isolated validation environment lacks the existing `passlib` runtime dependency.

## Next

Sprint 6 T11 should only add another layer after institutional access semantics are exercised in the real application environment. Candidate next work should preserve the distinction between institutional access, individual subscriptions, purchases, lifetime ownership, and entitlements.
