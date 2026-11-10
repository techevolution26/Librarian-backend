# Community resource contributions (backend)

## Domain boundary

`ResourceContribution` and `ResourceContributionAsset` represent a private member submission package. They are not catalogue `Book` / `ArchivalObject` records and do not reuse `CreatorBookSubmission`, which remains associated with CreatorAccount publication workflows.

Ordinary authenticated members may submit; Admins review and decide whether to import. An Admin's contribution approval only promotes source files into a draft catalogue record. The established archival rights-review and Book publication gates remain separate and mandatory.

## State flow

`submitted -> under_review -> (changes_requested -> submitted) | rejected | approved`

A member may withdraw a `submitted` or `changes_requested` item. A contribution can be imported at most once (`imported_book_id` is unique and approval rejects already imported or terminal states). `approved` means imported into draft, not publicly approved or published.

## Storage and fixity

Initial assets are stored below the private `community-contributions/` quarantine prefix. Their API representation includes filename, MIME, size and SHA-256 but never `storage_key`. The authenticated asset route resolves keys using the storage abstraction and checks owner/Admin authorization.

On approval, the backend rechecks every file's SHA-256 and existence, copies files to canonical archive storage, creates versioned `BookAsset` rows, current `AssetStorageLocation` records, ordered `ArchivalCanvas` rows for image assets, and ingestion/checksum preservation events. The contributor's user ID is retained as the source uploader attribution. Quarantine originals are removed only after the database transaction commits; cleanup is best-effort and must not delete a successfully promoted copy after a commit.

## Rights and visibility

Contributor rights-basis/evidence fields are declarations only. Imported `Book` and `ArchivalObject` records are created with draft visibility and `ArchivalRights.view_allowed = null`, with no verified timestamp. The public IIIF manifest/image/OCR contract must continue to fail closed. Only an independent Admin rights review can establish an access decision; the Admin must then explicitly publish the Book through the existing endpoint.

## Validation and authorization

- `USER` and other authenticated non-Admin members may submit and access only their own packages.
- Admin-only operations are queue listing, review, approval, and cross-member asset inspection. Review status changes and approvals create Admin activity log entries.
- Foreign item/attachment reads return 404; non-Admin use of Admin endpoints returns 403.
- Active pending limit defaults to five and is configurable via `MAX_PENDING_RESOURCE_CONTRIBUTIONS_PER_USER`.
- Uploads are restricted to PDF, UTF-8 text/Markdown and decoded JPEG/PNG/WebP images, bounded by existing file-size, aggregate-size, canvas-count, image-pixel limits.
- HTML, office files, executable formats, audio and video are not accepted in this workflow.

## API

See the route inventory and permissions in this document's mobile counterpart. Router prefix: `/community/resource-contributions`.

## Operations requiring follow-up

1. Define an explicit private-quarantine retention schedule and deletion/erasure workflow for withdrawn, rejected, abandoned, and approved submissions. Until then, files remain private and operators must monitor storage consumption.
2. Add source-file replacement for `changes_requested` if reviewer workflows require it; the first mobile correction screen updates metadata only.
3. Add hierarchical Collection and controlled creator-authority models separately; current contribution collection/creator values are descriptive strings, not authoritative linked records.
4. Complete PostgreSQL migration deployment and test multi-part uploads using actual local and cloud-backed mobile document providers.
