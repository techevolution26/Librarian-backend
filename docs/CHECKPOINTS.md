# The Librarian — Implementation Record

This consolidated record replaces the former per-tackle markdown files.

## Sprint 3

Implemented Circle invitations/lifecycle, community annotations, object/page discussions, curator/community authority separation, and moderation. Community records remain separate from archival authority.

## Sprint 4

Implemented storage abstraction, preservation masters/derivatives, replication, canvases, IIIF Presentation, IIIF Image API, archival viewer, OCR, and preservation verification.

## Sprint 5

Implemented creator accounts, dashboard, submissions, rights declarations, hosted books, paid offers, lifetime ownership, analytics, revenue accounting, payouts, and public creator profiles. Creator workspace navigation was subsequently integrated and repaired.

Core separation:

```text
Offer ≠ Purchase ≠ Ownership ≠ Entitlement ≠ Revenue ≠ Payout
```

## Sprint 6

- T1 Entitlement engine: durable book/feature access records and lifetime-access integration.
- T2 Plans: individual/institutional plan catalogue metadata.
- T3 Feature limits: disabled/finite/unlimited plan feature semantics.
- T4/T5 Bookmark/notebook limits: usage resolution and creation-boundary enforcement.
- T6 Advanced reader capabilities: explicit capability vocabulary.
- T7 Subscription billing: Stripe customer/subscription projection, Checkout, portal, webhook synchronization, effective-plan resolution.
- T8 Purchase entitlements: purchase lifecycle and verified provider events.
- T9 Lifetime ownership integration: verified purchases create/reactivate ownership and lifetime-access entitlement; refunds revoke the purchase-derived ownership path.
- T10 Institutional plans: institutions, memberships, seat limits, institutional subscriptions, manager authorization, effective-plan fallback.
- Native integration pass 1: native plan/billing/access/purchase/capability/institution surfaces and paid-offer discovery.
- Access & billing hardening: protected reader/content delivery now uses the backend access decision, closing alternate URL/file bypasses.

## Validation convention

Checkpoint notes historically recorded focused tests, compilation, migration heads, and package hashes. The consolidated documentation intentionally records the durable result rather than every historical command.

## Documentation cleanup

- Consolidated historical checkpoint markdown into `docs/` and removed stale per-tackle root files.
- Backend documentation is now organized as README, ARCHITECTURE, DEVELOPMENT, ROADMAP, DOMAINS, and CHECKPOINTS.
