from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authz import require_archival_curator, require_admin_user
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.archival_canvas import ArchivalCanvas
from app.models.archival_object import ArchivalObject
from app.models.book import Book
from app.models.book_asset import BookAsset
from app.models.user import User
from app.schemas.archival_canvas import ArchivalCanvasCreate, ArchivalCanvasRead, ArchivalCanvasUpdate

router = APIRouter(prefix="/archival-objects", tags=["archival-canvases"])


def _get_object(object_id: int, db: Session, *, public: bool = False) -> ArchivalObject:
    query = select(ArchivalObject).where(ArchivalObject.id == object_id)
    if public:
        query = query.where(ArchivalObject.archived_at.is_(None), ArchivalObject.visibility == "published")
    row = db.scalar(query)
    if not row:
        raise HTTPException(status_code=404, detail="Archival object not found")
    return row


def _validate_asset(object_row: ArchivalObject, asset_id: int | None, db: Session) -> BookAsset | None:
    if asset_id is None:
        return None
    asset = db.scalar(select(BookAsset).where(BookAsset.id == asset_id))
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    book = db.scalar(select(Book).where(Book.id == asset.book_id))
    if not book or book.archival_object_id != object_row.id:
        raise HTTPException(status_code=400, detail="Asset does not belong to this archival object")
    return asset


@router.get("/{object_id}/canvases", response_model=list[ArchivalCanvasRead])
def list_canvases(object_id: int, db: Session = Depends(get_db)) -> list[ArchivalCanvasRead]:
    object_row = _get_object(object_id, db, public=True)
    rows = db.scalars(
        select(ArchivalCanvas)
        .where(ArchivalCanvas.archival_object_id == object_row.id)
        .order_by(ArchivalCanvas.sequence.asc())
    ).all()
    return [ArchivalCanvasRead.model_validate(row) for row in rows]


@router.get("/admin/{object_id}/canvases", response_model=list[ArchivalCanvasRead])
def admin_list_canvases(
    object_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ArchivalCanvasRead]:
    require_admin_user(current_user)
    object_row = _get_object(object_id, db)
    rows = db.scalars(
        select(ArchivalCanvas)
        .where(ArchivalCanvas.archival_object_id == object_row.id)
        .order_by(ArchivalCanvas.sequence.asc())
    ).all()
    return [ArchivalCanvasRead.model_validate(row) for row in rows]


@router.post("/admin/{object_id}/canvases", response_model=ArchivalCanvasRead, status_code=201)
def create_canvas(
    object_id: int,
    payload: ArchivalCanvasCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ArchivalCanvasRead:
    object_row = _get_object(object_id, db)
    require_archival_curator(current_user, object_row.curator_user_id)
    _validate_asset(object_row, payload.asset_id, db)
    if db.scalar(select(ArchivalCanvas).where(ArchivalCanvas.archival_object_id == object_id, ArchivalCanvas.sequence == payload.sequence)):
        raise HTTPException(status_code=409, detail="Canvas sequence already exists")

    row = ArchivalCanvas(archival_object_id=object_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return ArchivalCanvasRead.model_validate(row)


@router.patch("/admin/{object_id}/canvases/{canvas_id}", response_model=ArchivalCanvasRead)
def update_canvas(
    object_id: int,
    canvas_id: int,
    payload: ArchivalCanvasUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ArchivalCanvasRead:
    object_row = _get_object(object_id, db)
    require_archival_curator(current_user, object_row.curator_user_id)
    row = db.scalar(select(ArchivalCanvas).where(ArchivalCanvas.id == canvas_id, ArchivalCanvas.archival_object_id == object_id))
    if not row:
        raise HTTPException(status_code=404, detail="Canvas not found")
    updates = payload.model_dump(exclude_unset=True)
    if "asset_id" in updates:
        _validate_asset(object_row, updates["asset_id"], db)
    if "sequence" in updates and db.scalar(select(ArchivalCanvas).where(
        ArchivalCanvas.archival_object_id == object_id,
        ArchivalCanvas.sequence == updates["sequence"],
        ArchivalCanvas.id != canvas_id,
    )):
        raise HTTPException(status_code=409, detail="Canvas sequence already exists")
    for field, value in updates.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return ArchivalCanvasRead.model_validate(row)


@router.delete("/admin/{object_id}/canvases/{canvas_id}", status_code=204)
def delete_canvas(
    object_id: int,
    canvas_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    object_row = _get_object(object_id, db)
    require_archival_curator(current_user, object_row.curator_user_id)
    row = db.scalar(select(ArchivalCanvas).where(ArchivalCanvas.id == canvas_id, ArchivalCanvas.archival_object_id == object_id))
    if not row:
        raise HTTPException(status_code=404, detail="Canvas not found")
    db.delete(row)
    db.commit()
