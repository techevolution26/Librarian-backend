# The Librarian — Sprint 4 T1 Storage Checkpoint

## T1 — Storage Abstraction & Archival Locations

Implemented the first Sprint 4 preservation/storage layer without replacing the working local upload pipeline.

### Changes

- Added `AssetStorageLocation` as the physical-storage record for a logical `BookAsset`.
- Kept `BookAsset` as the logical/versioned asset identity.
- Added storage provider values for:
  - `local`
  - `object_storage` (reserved for the durable backend implementation)
- Added physical storage status:
  - `active`
  - `unavailable`
  - `retired`
- Added primary-location, checksum, size, public URL, bucket, verification timestamp, and storage-key fields.
- Added `StorageBackend` protocol and `LocalStorageBackend` implementation.
- Routed fixity path resolution through the storage abstraction while preserving local filesystem behavior.
- Added `storage_provider` configuration, defaulting to `local`.
- Added Alembic migration `d7e8f9a0b1c2_add_asset_storage_locations.py`.
- Migration backfills one primary local storage location for every existing `BookAsset`.
- New PDF and cover uploads now create their primary physical storage-location record in the same database transaction as the asset.

### Deliberate non-changes

- No object-storage SDK was added.
- No existing uploaded file was moved.
- No existing `BookAsset` storage key was rewritten.
- The working mobile upload path remains unchanged.
- `BookAsset` was not converted into a page/Canvas model.
- No IIIF API or viewer was introduced in T1.

### Validation

- `python -m compileall -q app` — passed.
- Python AST parsing of changed source files — passed.
- `alembic heads` — `d7e8f9a0b1c2 (head)`.
- Full application/database migration was not executed in this isolated checkpoint because the checkpoint environment's configured database driver/runtime is not available.
