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
