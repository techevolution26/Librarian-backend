# Admin archival ingestion contract

This document describes the supported Admin ingestion workflow and the backend guarantees. It intentionally excludes the contents of the runtime `storage/` directory.

## Supported primary representations

The Admin ingestion endpoint is `POST /books/ingest`. It creates a **draft Book** and a linked **ArchivalObject**, then records the source and its provenance as independently identifiable records.

| Primary representation | Accepted source | Reader delivery |
| --- | --- | --- |
| PDF | PDF with a valid `%PDF-` signature | Existing protected Book Content/PDF reader path |
| Plain text | UTF-8 `.txt` or `.md` | Native text Reader path |
| Image-only facsimile | One or more JPEG, PNG, or WebP images | Ordered IIIF canvases and image delivery |

PDF and text primary records may also include supplementary scanned images. These become separate IIIF canvases; they do not replace or masquerade as the primary PDF/text source. An image-only facsimile uses IIIF canvases as its primary representation.

Audio, video, office documents, spreadsheets, and arbitrary binaries are **not** accepted as primary Reader materials. The source-anchor model's media-time locator does not mean a protected media delivery/player exists.

## Asset identity and versioning

- The Book is the catalogue-facing identity.
- The linked ArchivalObject owns archival description, provenance, rights, and the canvas sequence.
- Each PDF/text source is a versioned BookAsset with a singleton logical key (`NULL`).
- Each canvas image is a separately versioned BookAsset whose `logical_key` is the stable `canvas_identifier`.
- Replacing a canvas image keeps the canvas identifier and creates a new asset version; the previous asset becomes non-current and an `access_withdrawn` preservation event records the retired access version.
- Removing a canvas retains its binary asset for preservation history, marks it non-current when no other canvas references it, and records an `access_withdrawn` event.
- Image file storage paths are private storage keys, not public source URLs. Protected endpoints serve content after authorization.

The `f5c8d1a2b3c4_add_logical_asset_keys` Alembic migration adds logical keys and partial uniqueness indexes. Do not deploy application code requiring `logical_key` before applying the migration.

## Limits and validation

Current defaults are configured centrally:

- PDF: 150 MB per file.
- UTF-8 text: 20 MB per file.
- Archival image: 40 MB per file.
- Catalogue cover: 10 MB per file.
- Total current access assets in an ingest/source-set operation: 512 MB.
- Canvas count: 200 per ArchivalObject.
- Decoded image area: at most 100 megapixels per image.

JPEG, PNG, and WebP image signatures and decoded dimensions are checked; the stored MIME type is derived from the decoded image format rather than trusting the uploaded filename suffix. PDF signatures are checked. Text is decoded strictly as UTF-8; invalid encodings, empty payloads, and NUL-containing binary data are rejected without lossy conversion. The backend checks both per-file and aggregate limits when adding/replacing canvases.

## Rights lifecycle

New records start as drafts. Rights review defaults to `pending`. An `allow` decision requires a recorded evidence/source reference. Public manifest, canvas image, and OCR delivery require an explicit `allow` decision and a verification timestamp.

Adding, replacing, or deleting source canvases invalidates the prior rights decision and moves the Book and ArchivalObject back to draft. Public IIIF delivery is withdrawn until an authorised curator records a fresh decision and republishes the record. Renaming or reordering canvases does not change the underlying source set and does not itself invalidate rights.

PDF/text replacement also invalidates the prior rights review for a linked ArchivalObject. Admin OCR generation and verification are available for draft canvases through authenticated curator routes; this does not publish the source.

A catalogue cover is public catalogue artwork, not a protected source asset. Administrators must not upload a restricted source scan as a catalogue cover. The actual source images belong in the canvas ingestion workflow and remain rights-gated.

## Admin operations

- Initial ingest: `POST /books/ingest`.
- Add canvases to an existing Book: `POST /books/{book_id}/canvases`.
- Replace a canvas image/version: `PATCH /books/{book_id}/canvases/{canvas_id}/image`.
- Update a text source/version: `PATCH /books/{book_id}/update-text`.
- List, relabel, reorder, or delete canvases: curator IIIF canvas Admin routes.
- Generate and re-check OCR: authenticated Admin OCR routes.
- Record an explicit rights decision: `POST /archival-objects/admin/{id}/rights-review`.
- Publish catalogue/archival visibility only after a digital representation and completed rights review exist.

Text transcription editing is intentionally not offered by this workflow. A future editor needs its own revision history, source-fixity association, editor identity, and independent transcription-verification process; an image checksum alone cannot prove transcription accuracy.

## Test coverage

`tests/test_admin_multi_material_ingestion.py` exercises UTF-8 text plus multiple scans, PDF plus supplementary scans, image-only facsimile validation, rights review and publishing, add/replace lifecycle, stable canvas identity, aggregate replacement limits, and preservation of the previous current asset after a rejected replacement.


## Preservation dashboard API

`GET /preservation-events/admin/{archival_object_id}/dashboard` returns the object's asset versions, storage-copy status, and append-only preservation events for the Admin workspace. The response deliberately excludes physical storage keys and public URLs. Asset fixity is verified using `POST /fixity/admin/objects/{archival_object_id}/verify`; replica creation remains available through the existing Admin book-asset replica route and currently supports the configured local storage provider only.
