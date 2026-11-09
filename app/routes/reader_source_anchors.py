from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import TypeAdapter

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.reader_source_anchor import ReaderSourceAnchor
from app.models.user import User
from app.schemas.reader_source_anchor import (
    ReaderSourceAnchorCreate,
    ReaderSourceAnchorRead,
    ReaderSourceLocator,
)
from app.services.reader_source_anchors import create_reader_source_anchor, is_source_anchor_current

router = APIRouter(prefix="/reader/source-anchors", tags=["reader-source-anchors"])
_locator_adapter = TypeAdapter(ReaderSourceLocator)


def _read(db: Session, row: ReaderSourceAnchor) -> ReaderSourceAnchorRead:
    return ReaderSourceAnchorRead(
        id=row.id,
        user_id=row.user_id,
        book_id=row.book_id,
        archival_object_id=row.archival_object_id,
        locator=_locator_adapter.validate_python(row.locator_data),
        source_persistent_identifier=row.source_persistent_identifier,
        source_accession_number=row.source_accession_number,
        source_canvas_identifier=row.source_canvas_identifier,
        source_asset_id=row.source_asset_id,
        source_asset_version=row.source_asset_version,
        source_asset_checksum_sha256=row.source_asset_checksum_sha256,
        source_text_sha256=row.source_text_sha256,
        source_is_current=is_source_anchor_current(db, row),
        created_at=row.created_at,
    )


@router.post("", response_model=ReaderSourceAnchorRead, status_code=status.HTTP_201_CREATED)
def create_source_anchor(
    payload: ReaderSourceAnchorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReaderSourceAnchorRead:
    row = create_reader_source_anchor(
        db,
        user=current_user,
        book_id=payload.book_id,
        locator=payload.locator,
    )
    return _read(db, row)


@router.get("", response_model=list[ReaderSourceAnchorRead])
def list_source_anchors(
    book_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ReaderSourceAnchorRead]:
    query = select(ReaderSourceAnchor).where(ReaderSourceAnchor.user_id == current_user.id)
    if book_id is not None:
        query = query.where(ReaderSourceAnchor.book_id == book_id)
    rows = db.scalars(query.order_by(ReaderSourceAnchor.created_at.desc(), ReaderSourceAnchor.id.desc())).all()
    return [_read(db, row) for row in rows]


@router.get("/{anchor_id}", response_model=ReaderSourceAnchorRead)
def get_source_anchor(
    anchor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReaderSourceAnchorRead:
    row = db.scalar(
        select(ReaderSourceAnchor).where(
            ReaderSourceAnchor.id == anchor_id,
            ReaderSourceAnchor.user_id == current_user.id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Reader source anchor not found")
    return _read(db, row)


@router.delete("/{anchor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source_anchor(
    anchor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    row = db.scalar(
        select(ReaderSourceAnchor).where(
            ReaderSourceAnchor.id == anchor_id,
            ReaderSourceAnchor.user_id == current_user.id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Reader source anchor not found")
    # Existing reader records retain their legacy page/quote data. Their FK is
    # nulled by ON DELETE SET NULL; no archival record is touched.
    db.delete(row)
    db.commit()
