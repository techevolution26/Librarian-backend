# The Librarian — Sprint 4 T3 Checkpoint

## Replication & Storage Copies

Implemented on top of Sprint 4 T2.

### What changed

- Extended `AssetStorageLocation` so each physical copy can record:
  - `replicated_from_location_id`
  - `replication_status`
  - `replication_error`
- Added explicit replication states:
  - `none`
  - `pending`
  - `copying`
  - `verified`
  - `failed`
- Added a self-referential storage-location relationship so replica lineage is explicit.
- Extended the storage backend contract with a copy operation.
- Implemented safe local-backend copying through the existing storage-root path traversal protection.
- Added admin endpoint to list physical storage locations for an asset.
- Added admin endpoint to create a replica:
  - verifies source availability
  - creates a distinct storage location
  - copies the bytes
  - recomputes SHA-256
  - verifies size
  - marks the replica `verified`
  - records `storage_replication` in append-only preservation history
  - records failed attempts as `failed` with an error and preservation event
- Added `AssetStorageLocationRead` schema for administrative inspection.
- Added migration `f0a1b2c3d4e5`.

### Current provider boundary

T3 implements the local provider only. This is intentionally **not** presented as durable multi-site/object-storage replication. The physical copy is nevertheless modeled through `AssetStorageLocation`, so a future object-storage backend can implement the same replication contract without changing `BookAsset` identity.

### Validation performed

- `python -m compileall -q app` — passed.
- `alembic heads` — single head: `f0a1b2c3d4e5`.
- Local storage copy test — passed: copied bytes, SHA-256, and size matched.
- Static T3 contract checks — passed.

### Not claimed

Full application startup, database migration execution, and runtime API integration were not claimed because the isolated checkpoint environment retains the previously documented database-driver limitation.
