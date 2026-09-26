# Sprint 4 T6 — IIIF Image API Checkpoint

## Implemented

- Added IIIF Image API 3.0 image-service endpoints:
  - `GET /iiif/3/{canvas_identifier}/info.json`
  - `GET /iiif/3/{canvas_identifier}/{region}/{size}/{rotation}/{quality}.{format}`
- Added Pillow as the required image-processing dependency (`Pillow==12.3.0`).
- Added image inspection and transformation service with:
  - pixel and percentage regions
  - square regions
  - width/height/confined sizes
  - percentage sizes
  - 90-degree rotation increments
  - default/color/gray quality
  - JPEG, PNG, and WebP output
- Explicitly rejects mirroring, arbitrary-angle rotation, and upscaling because those capabilities are not advertised by this implementation.
- Added IIIF `info.json` metadata with ImageService3, level1 profile, supported qualities/formats/features, and rights URI when applicable.
- Added Image API service metadata to Presentation 3 image bodies in the existing manifest builder.
- Added CORS/cache/security headers on image responses.

## Archival safety boundary

An image is served only when all of the following are true:

- archival object is published and not archived;
- canvas points to a current `access` BookAsset;
- asset MIME type is an image;
- an active physical storage location exists;
- the location is either the original/primary (`replication_status=none`) or a verified replica;
- the location provider matches the configured storage backend;
- archival rights do not explicitly set `view_allowed=False`.

Preservation masters are never eligible for the public Image API.

## Validation

- `python -m compileall -q app tests` — passed
- `PYTHONPATH=. pytest -q tests/test_iiif_image.py` — **5 passed**
- `alembic heads` — `c1d2e3f4a5b6 (head)`
- Full test suite remains environment-blocked during collection because the isolated checkpoint `.env` points at MySQL while `pymysql` is not installed.
- Full application import could not be completed in the isolated environment because its available Python environment also lacks the `psycopg` package required by the project's PostgreSQL dependency declaration. No runtime/database integration claim is made from this checkpoint.

## Standards reference

Implementation follows the IIIF Image API 3.0 URI structure and Image Information model. The service declares only the capabilities it actually implements.
