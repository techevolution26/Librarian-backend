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
