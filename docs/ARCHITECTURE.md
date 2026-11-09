# The Librarian — Backend Architecture

## Purpose

The backend is the authoritative FastAPI service for The Librarian. It owns business rules, authorization, persistence, archival integrity, billing state, and access decisions for both web and Expo native clients.

## Core stack

- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- JWT authentication
- local development storage behind a storage abstraction
- Stripe Billing integration for subscription/purchase billing

## Domain boundaries

```text
Catalogue / Archive
 ├── Book
 ├── ArchivalObject
 ├── BookAsset
 ├── Metadata / Provenance / Rights
 ├── PreservationEvent
 ├── Canvas / IIIF
 └── OCR

Reader
 ├── LibraryItem
 ├── Bookmark
 ├── Highlight
 ├── Note / Notebook
 └── QuoteReference

Community
 ├── Connections
 ├── Circles
 ├── Annotations
 ├── Discussions
 └── Moderation

Creator
 ├── CreatorAccount
 ├── Submission
 ├── RightsDeclaration
 ├── HostedBook
 ├── PaidOffer
 ├── LifetimeAccess
 ├── RevenueLedger
 └── Payout

Subscriptions / Access
 ├── SubscriptionPlan
 ├── PlanFeatureLimit
 ├── Subscription
 ├── Entitlement
 ├── Purchase
 └── Institution / Membership / Subscription
```

## Authorization

Authorization is server-side. Native/web visibility is never the security boundary.

Important access chain:

```text
Subscription / Institution
        ↓
Effective Plan
        ↓
Feature configuration

Purchase / Lifetime Ownership
        ↓
Entitlement
        ↓
Book access decision
        ↓
Protected content delivery
```

Protected content must not be reachable through an unguarded alternate file path.

## Archival authority

Admin has global archival authority. Assigned curators receive only the explicit authority granted to their assigned archival objects. Community records cannot mutate archival metadata, rights, provenance, or preservation state.

## Creator and billing boundaries

- Creator rights declarations are not archival rights.
- Paid offers are not purchases.
- Purchases are not entitlements.
- Lifetime ownership is not accounting.
- Revenue ledger entries are immutable accounting records.
- Payout allocations are settlement records and do not mutate revenue entries.
- Subscription billing is separate from creator revenue accounting.

## Storage and preservation

`BookAsset` represents a logical asset. Physical storage is behind storage-location/provider abstractions. Preservation masters, derivatives, replication, checksums, OCR, and preservation events remain distinct from public access copies.

## Source-native Reader research

Reader research uses an additive `ReaderSourceAnchor` record rather than
reinterpreting every location as a numbered Book page. An anchor is owned by
one user and scoped to one Book. It stores a typed locator and immutable
snapshots of the source identity that was referenced (persistent identifier,
canvas identifier, asset version/checksum, and/or exact transcription hash).

Supported locator contracts:

- `pdf_page`: a one-based page in a specific access-PDF asset version.
- `pdf_text`: a page-local Unicode-codepoint range in a specific access-PDF
  asset version.
- `iiif_canvas`: a stable IIIF canvas identifier, not a PDF page number.
- `image_region`: a pixel- or percentage-based region on a current access
  image canvas.
- `text_span`: a Unicode-codepoint range in the Book's plain-text body,
  bound to its SHA-256 snapshot.
- `ocr_span`: a Unicode-codepoint range in an explicitly verified OCR record
  whose source asset and checksum still match the selected canvas.
- `media_time`: a time range on a current access audio/video asset with a
  matching media canvas and a recorded duration. The locator is modelled and
  validated; a protected media playback/delivery surface is still a separate
  capability and must exist before clients treat the media as playable.

The legacy `page_number` columns remain for existing clients and PDF locators.
Non-PDF anchors never map to a fabricated page number. `Highlight.page_number`
is nullable to allow highlights attached to non-paginated sources. Anchors are
not archival metadata and are not shared with Circle annotations. Deleting an
anchor only nulls its Reader-record foreign keys; the user's saved text, notes,
quote, and any legacy PDF page data remain intact.

Creating an anchor requires both the authoritative Book access decision and,
for archival sources, a published ArchivalObject with viewing rights. Anchors
are immutable through the API; clients create a new anchor when the source
location or source version changes. The server never stores a duplicate copy
of the selected document/transcription inside an anchor.

The read API computes `source_is_current` at request time. It compares asset
identity, current-version state, version, and recorded checksum; OCR anchors
also require the same verified OCR record and source asset/checksum, while
plain-text anchors compare the exact current transcription hash. `false`
means a saved range must not be silently applied to a replacement source;
`true` means the current source identity can be resolved; `null` means the
available locator has no versioned source evidence to compare. This is a
resolution hint only: it does not mutate the immutable anchor, verify storage
fixity, or grant access to the source.
