# Sprint 4 T4 — Page / Canvas Model

Implemented a logical archival canvas layer without conflating canvases with stored BookAsset files.

## Model
- `ArchivalCanvas` belongs to an `ArchivalObject`.
- Each canvas has a stable `canvas_identifier`.
- `sequence` defines presentation order.
- `page_number` is optional for page-bearing material.
- `label`, media type, width, height, and duration are modeled for future IIIF/media presentation.
- `asset_id` optionally identifies the stored source asset; the canvas remains a logical presentation unit.

## API
- Public list: `GET /archival-objects/{object_id}/canvases`
- Admin list: `GET /archival-objects/admin/{object_id}/canvases`
- Admin create/update/delete canvas endpoints.
- Asset references are validated against the archival object's linked Book.
- Archival mutation uses the existing explicit curator/admin authority boundary.

## Migration
`c1d2e3f4a5b6_add_archival_canvases.py`

## Validation
- `python -m compileall -q app` passed.
- `alembic heads` reports one head: `c1d2e3f4a5b6`.
- Static T4 contract checks passed.
- Full runtime/database integration was not claimed because the isolated checkpoint retains the documented database-driver/environment limitation.

## Boundary
This is the page/canvas data foundation only. IIIF Presentation Manifest generation, Image API delivery, and viewer behavior remain separate tackles.
