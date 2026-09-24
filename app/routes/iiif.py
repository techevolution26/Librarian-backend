from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import Depends

from app.core.database import get_db
from app.models.archival_object import ArchivalObject
from app.schemas.iiif import IIIFReadyProfile
from app.services.iiif import build_iiif_ready_profile

router = APIRouter(prefix="/archival-objects", tags=["iiif"])


@router.get("/{object_id}/iiif/profile", response_model=IIIFReadyProfile)
def get_iiif_ready_profile(object_id: int, db: Session = Depends(get_db)) -> IIIFReadyProfile:
    row = db.scalar(
        select(ArchivalObject).where(
            ArchivalObject.id == object_id,
            ArchivalObject.archived_at.is_(None),
            ArchivalObject.visibility == "published",
        )
    )
    if not row:
        raise HTTPException(status_code=404, detail="Archival object not found")
    return build_iiif_ready_profile(row)
