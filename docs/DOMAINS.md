# The Librarian — Backend Domain Guide

## Archive

`Book` is the catalogue/reading identity. `ArchivalObject` is the stable archival identity. `BookAsset` represents logical files. Metadata, provenance, rights, preservation events, canvases, IIIF, OCR, and fixity belong to the archival layer.

## Reader

Bookmarks, highlights, notes, notebook records, and quote references are reader-owned records. They must not mutate archival authority.

## Community

Connections and Circles are social/community records. Circle annotations and discussions remain Circle-scoped. Moderation changes community state; it does not confer archival authority.

## Creator economy

Creator submissions become hosted/catalog records through explicit lifecycle steps. Rights declarations are creator assertions and do not replace archival rights.

Accounting is separate from access:

```text
Purchase → Revenue Ledger → Eligible Balance → Payout
```

## Subscription and access

```text
Plan catalogue
 ↓
Subscription / Institution subscription
 ↓
Effective plan
 ↓
Feature limits / capabilities

Purchase / Lifetime ownership
 ↓
Entitlement
 ↓
Access decision
```

A plan is not a subscription. A purchase is not an entitlement. An entitlement is the access authority.

## Authority

- Admin: global archival/platform authority.
- Assigned curator: explicit authority over assigned archival object.
- Circle owner/admin: Circle moderation authority.
- Community: no archival mutation authority.

## Reader source anchors

`ReaderSourceAnchor` is a private, user-owned locator that connects a Reader
record to a precise source location without changing archival authority.
Supported typed locators cover PDF page/text positions, stable IIIF canvas IDs,
image regions, Book text spans, verified OCR spans, and bounded audio/video
time ranges when an access media asset and duration exist.

A source anchor snapshots the relevant archival persistent identifier, canvas
identifier, asset version and SHA-256 checksum, and/or source-text SHA-256. A
locator never stores a storage key or public/protected file URL. PDF anchors may
also populate the legacy `page_number`; canvas, image, transcription, OCR and
media locators must not be represented as Book pages.

Bookmarks, highlights, private Notebook notes, and quote references may attach
to an anchor. Existing page-only records remain valid. Circle annotations are
independent, Circle-scoped community records and do not consume Reader anchors. QuoteReference responses format source-aware citations from the anchor type and immutable source snapshot: PDF pages/text ranges, canvas identifiers and labels, image-region coordinates, OCR/plain-text offsets, and media time ranges. Legacy page-only citations remain compatible.


Anchor read responses include a computed `source_is_current` hint. Asset-backed
anchors are compared against the recorded current asset/version/checksum;
OCR additionally checks that the captured OCR record is still verified and
bound to the same source asset/checksum. Book text spans compare the current
transcription hash. The value is `null` when no comparable version/hash exists.
It is intentionally computed at read time and does not rewrite the source
snapshot or replace storage fixity verification.
