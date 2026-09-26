from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models.archival_canvas import ArchivalCanvas
from app.models.archival_object import ArchivalObject
from app.schemas.iiif import IIIFManifest, IIIFReadyProfile
from app.services.iiif import build_iiif_manifest, build_iiif_ready_profile

router = APIRouter(prefix="/archival-objects", tags=["iiif"])


def _public_object(object_id: int, db: Session) -> ArchivalObject:
    row = db.scalar(
        select(ArchivalObject)
        .options(
            selectinload(ArchivalObject.intellectual_metadata),
            selectinload(ArchivalObject.provenance),
            selectinload(ArchivalObject.rights),
            selectinload(ArchivalObject.canvases).selectinload(ArchivalCanvas.asset),
        )
        .where(
            ArchivalObject.id == object_id,
            ArchivalObject.archived_at.is_(None),
            ArchivalObject.visibility == "published",
        )
    )
    if not row:
        raise HTTPException(status_code=404, detail="Archival object not found")
    return row


@router.get("/{object_id}/iiif/profile", response_model=IIIFReadyProfile)
def get_iiif_ready_profile(
    object_id: int, db: Session = Depends(get_db)
) -> IIIFReadyProfile:
    return build_iiif_ready_profile(_public_object(object_id, db))


@router.get("/{object_id}/iiif/manifest", response_model=IIIFManifest)
def get_iiif_manifest(
    object_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> IIIFManifest:
    row = _public_object(object_id, db)
    manifest_id = str(request.url).split("?", 1)[0]
    return build_iiif_manifest(row, manifest_id)
