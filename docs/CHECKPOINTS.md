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

## Sprint 7 — T5 Source-native Reader anchors (2026-11-06)

Implemented an additive `ReaderSourceAnchor` model and `/reader/source-anchors`
API. Typed locators distinguish PDF page and page-local text, IIIF canvas,
image region, Book text span, verified OCR span, and bounded audio/video time
ranges. Anchors preserve source persistent identifiers, canvas identifiers,
asset version/checksum, and/or transcription checksum as immutable snapshots.

Bookmarks, highlights, private Notebook notes, and quote references can attach
to user-owned anchors. Existing `book_id` and `page_number` fields remain
available; only PDF anchors populate the legacy page field. Circle annotations
were not modified. The Alembic revision is
`e4b7c9d2a601_add_reader_source_anchors.py`, based on
`d1e2f3a4b5c6`.

Focused validation: 13 source-anchor tests pass. Full suite, production
PostgreSQL migration execution, and native client integration remain to be
verified in the project environment. The repository's local `.env` is
intentionally not included in generated source checkpoints; use `.env.example`
for local setup. The `storage/` directory and its PDF files were excluded from
this tackle and checkpoint.


## Sprint 7 — T5.7 Expo Reader source-anchor integration (2026-11-06)

Paired the T4 native Reader checkpoint with the T5 backend source-anchor
checkpoint. The mobile client now creates and retrieves typed source anchors,
attaches them to Bookmarks, Highlights, Notebook Notes, and QuoteReferences,
and restores source-native locations from Notebook.

Supported native capture/restore paths: PDF page and text range, plain-text
range, IIIF canvas, image region, and verified OCR range. Unicode-codepoint
source offsets are converted at React Native UTF-16 selection boundaries.
The backend exposes a read-time `source_is_current` resolution hint so stale
PDF/transcription/OCR/image-region ranges are not silently restored against a
replacement source. Legacy page-only records remain supported. Compatibility
fallback is intentionally limited to an absent source-anchor route and PDF
page workflows; validation/access/not-found/conflict responses are surfaced.

Notebook note cards and formal citation cards now have explicit Open source
actions. Highlight-to-Notebook development and QuoteReference creation retain
the source anchor. Circle annotation models/routes are unchanged. Media-time
locators remain backend-only pending protected media delivery/playback.

Validation: the mobile source tree has 74 TypeScript/TSX files with zero
transpilation/syntax diagnostics. Full TypeScript semantic checking and
Android/iOS runtime acceptance remain pending because this checkpoint excludes
`node_modules` and Expo SDK type declarations. The paired backend full suite
passes 150 tests under the documented test-only `passlib` import shim; Python
compilation and migration graph validation are run separately. No `storage/`
folder, PDF, or private `.env` is packaged.
