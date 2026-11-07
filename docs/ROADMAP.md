# The Librarian — Roadmap

## Current completed foundation

### Sprint 4 — IIIF & Preservation

🟢 Storage abstraction · preservation masters/derivatives · replication · canvases · IIIF Presentation · IIIF Image API · archival viewer · OCR/preservation verification.

### Sprint 5 — Creator Economy

🟢 Creator accounts · dashboard · submissions · rights declarations · hosted books · paid offers · lifetime ownership · analytics · revenue accounting · payouts · public creator profile/domain surface · creator workspace integration.

### Sprint 6 — Subscriptions & Access

🟢 Entitlement engine · plans · feature limits · bookmark limits · notebook limits · advanced reader capabilities · subscription billing · purchase entitlements · lifetime ownership integration · institutional plans · native integration pass 1 · access/billing hardening.

### Sprint 3 — Living Archive

Historical implementation exists for connections/circles, invitations, community annotations, discussions, authority separation, and moderation. The formal sprint board should be reconciled against current acceptance criteria before declaring the sprint closed.

## Current decision point

Sprint 6 has a coherent access and billing foundation. Do not add another tackle solely to increase the sprint count. Choose the next sprint from a concrete product requirement and define its backend/native boundaries before implementation.

## Sprint 7 — Source-native Reader research

- 🟢 T5.1 Typed source-anchor model and API for PDF page/text, IIIF canvas,
  image-region, Book text-span, verified OCR-span, and bounded media-time
  locators.
- 🟢 T5.2 Backward-compatible attachment points for bookmarks, highlights,
  private Notebook notes, and quote references.
- 🟢 T5.3 Access/ownership/Book-scope checks and immutable source-version/hash
  snapshots; no storage URLs or Circle data are exposed.
- 🟢 T5.4 Alembic migration and focused locator/validation tests.
- 🟡 T5.5 Protected media delivery/playback before media-time anchors become a
  user-facing Reader workflow.
- 🟡 T5.6 Native client integration, citation rendering, and migration of
  client-created research records to source anchors.
