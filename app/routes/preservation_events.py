from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authz import require_admin_user
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.archival_object import ArchivalObject
from app.models.book import Book
from app.models.book_asset import BookAsset
from app.models.preservation_event import PreservationEvent
from app.models.user import User
from app.schemas.preservation_event import PreservationEventCreate, PreservationEventRead

router = APIRouter(prefix="/preservation-events", tags=["preservation"])


def _read(row: PreservationEvent) -> PreservationEventRead:
    return PreservationEventRead.model_validate(row)


@router.get("/admin/{object_id}", response_model=list[PreservationEventRead])
def list_preservation_events(
    object_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PreservationEventRead]:
    require_admin_user(current_user)

    if not db.scalar(select(ArchivalObject).where(ArchivalObject.id == object_id)):
        raise HTTPException(status_code=404, detail="Archival object not found")

    rows = db.scalars(
        select(PreservationEvent)
        .where(PreservationEvent.archival_object_id == object_id)
        .order_by(PreservationEvent.event_date.desc(), PreservationEvent.id.desc())
    ).all()
    return [_read(row) for row in rows]


@router.post("/admin/{object_id}", response_model=PreservationEventRead, status_code=201)
def create_preservation_event(
    object_id: int,
    payload: PreservationEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PreservationEventRead:
    require_admin_user(current_user)

    if not db.scalar(select(ArchivalObject).where(ArchivalObject.id == object_id)):
        raise HTTPException(status_code=404, detail="Archival object not found")

    asset = None
    if payload.asset_id is not None:
        asset = db.scalar(select(BookAsset).where(BookAsset.id == payload.asset_id))
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        asset_object_id = db.scalar(
            select(Book.archival_object_id).where(Book.id == asset.book_id)
        )
        if asset_object_id != object_id:
            raise HTTPException(status_code=400, detail="Asset does not belong to this archival object")

    event = PreservationEvent(
        archival_object_id=object_id,
        asset_id=payload.asset_id,
        event_type=payload.event_type,
        event_date=payload.event_date or datetime.now(timezone.utc),
        outcome=payload.outcome,
        agent=payload.agent or current_user.full_name,
        detail=payload.detail,
        source_storage_key=payload.source_storage_key,
        target_storage_key=payload.target_storage_key,
        checksum=payload.checksum,
        checksum_algorithm=payload.checksum_algorithm,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return _read(event)
