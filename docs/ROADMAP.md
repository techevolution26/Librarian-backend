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
  user-facing Reader workflow; the Expo client does not expose media-time controls.
- 🟢 T5.6 Expo integration for PDF page/text, Book text span, IIIF canvas,
  image-region, and verified OCR anchors; Bookmarks, Highlights, Notes, and
  QuoteReferences preserve `source_anchor_id` and Notebook return-to-source.
- 🟡 T5.7 Live PostgreSQL/API deployment and native SDK 57 device acceptance;
  media playback remains a separate future capability.


## Admin archival ingestion — multi-material support

- 🟢 `POST /books/ingest` supports PDF, strict UTF-8 text, and image-only facsimile primary representations.
- 🟢 PDF/text may include supplementary ordered JPEG/PNG/WebP IIIF canvases.
- 🟢 Existing Books can gain canvases; each canvas has a stable logical asset key and independent version history.
- 🟢 Canvas replacement preserves the canvas identifier, enforces aggregate limits, and records preservation events.
- 🟢 Adding/replacing/deleting source canvases invalidates the previous rights decision and withdraws public IIIF delivery until re-review.
- 🟢 Rights `allow` requires an evidence/source reference; public IIIF manifest, image, and OCR delivery fail closed without a verified allow decision.
- 🟢 Admin OCR generate/recheck works on draft materials through authenticated curator routes.
- 🟡 Audio/video/office formats remain unsupported as primary Reader materials pending protected delivery and native playback/presentation.
- 🟡 PostgreSQL migration `f5c8d1a2b3c4` and production deployment validation are required before running this code against the production database.


## Admin metadata and preservation workspace — 2026-11-10

- ✅ Admin-only preservation dashboard aggregates logical assets, physical storage-copy states and append-only events without exposing storage keys or public URLs.
- ✅ Existing ArchivalObject PATCH API supports the dedicated descriptive metadata/provenance editor; rights decisions stay on the auditable rights-review endpoint.
- 🟡 Collection hierarchy and controlled creator authority are not represented in the current schema. A single `collection_id` assignment must not be presented as a nested archival hierarchy.
- 🟡 Replication currently implements the configured local provider; object-storage provider replication needs a provider-specific copy implementation.


## Community resource contributions — 2026-11-10

- ✅ Standard authenticated members can upload private PDF, UTF-8 text, and image-only facsimile submissions with ordered supplementary canvases.
- ✅ Quarantine package records are separate from Books/ArchivalObjects; owner/Admin authorization protects metadata and source-asset access.
- ✅ Admin queue/review endpoints support submitted, under-review, changes-requested, rejected, approved and withdrawn status views.
- ✅ Admin approval promotes verified source files into a draft Book and ArchivalObject, preserves contributor uploader attribution, checksums, storage-location records, canvases and preservation events.
- ✅ Imported archival rights remain unverified and public IIIF remains closed until independent Admin rights review and explicit Book publication.
- ✅ Approval rollback no longer deletes successfully promoted files after a successful database commit; quarantine cleanup is best-effort after commit.
- 🟡 A retention/erasure policy and scheduled cleanup for private quarantine assets is still needed. Until then, operators must monitor quarantine volume; rejected/withdrawn assets remain private rather than being silently purged.
- 🟡 Source-file replacement during contributor correction and hierarchical Collection/creator-authority resolution remain future capabilities.
- 🟢 Validation: **167 backend tests passed**, Python compilation passed, Alembic single head `f6d7e8a9b0c1`.
