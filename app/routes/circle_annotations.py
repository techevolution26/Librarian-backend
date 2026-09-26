from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.circle_annotation import CircleAnnotation
from app.models.circle_book import CircleBook
from app.models.circle_member import CircleMember
from app.models.user import User
from app.schemas.circle_annotations import (
    CircleAnnotationCreate,
    CircleAnnotationRead,
    CircleAnnotationUpdate,
)

router = APIRouter(prefix="/circles/{circle_id}/annotations", tags=["circle annotations"])


def require_member(db: Session, circle_id: int, user_id: int) -> CircleMember:
    member = db.scalar(
        select(CircleMember).where(
            CircleMember.circle_id == circle_id,
            CircleMember.user_id == user_id,
            CircleMember.status == "active",
        )
    )
    if not member:
        raise HTTPException(status_code=403, detail="Not a circle member")
    return member


def get_annotation(db: Session, circle_id: int, annotation_id: int) -> CircleAnnotation:
    annotation = db.scalar(
        select(CircleAnnotation)
        .where(
            CircleAnnotation.id == annotation_id,
            CircleAnnotation.circle_id == circle_id,
            CircleAnnotation.deleted_at.is_(None),
        )
        .options(joinedload(CircleAnnotation.user))
    )
    if not annotation:
        raise HTTPException(status_code=404, detail="Community annotation not found")
    return annotation


def validate_circle_book(db: Session, circle_id: int, circle_book_id: int) -> CircleBook:
    circle_book = db.scalar(
        select(CircleBook).where(
            CircleBook.id == circle_book_id,
            CircleBook.circle_id == circle_id,
            CircleBook.status == "active",
        )
    )
    if not circle_book:
        raise HTTPException(status_code=404, detail="Circle book not found")
    return circle_book


@router.get("/", response_model=list[CircleAnnotationRead])
def list_annotations(
    circle_id: int,
    circle_book_id: int | None = None,
    page_number: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CircleAnnotationRead]:
    require_member(db, circle_id, current_user.id)

    query = (
        select(CircleAnnotation)
        .where(
            CircleAnnotation.circle_id == circle_id,
            CircleAnnotation.deleted_at.is_(None),
        )
        .options(joinedload(CircleAnnotation.user))
    )
    if circle_book_id is not None:
        query = query.where(CircleAnnotation.circle_book_id == circle_book_id)
    if page_number is not None:
        query = query.where(CircleAnnotation.page_number == page_number)

    rows = db.scalars(
        query.order_by(CircleAnnotation.created_at.desc(), CircleAnnotation.id.desc())
    ).all()
    return [CircleAnnotationRead.model_validate(row) for row in rows]


@router.post("/", response_model=CircleAnnotationRead, status_code=status.HTTP_201_CREATED)
def create_annotation(
    circle_id: int,
    payload: CircleAnnotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CircleAnnotationRead:
    require_member(db, circle_id, current_user.id)
    circle_book = validate_circle_book(db, circle_id, payload.circle_book_id)

    row = CircleAnnotation(
        circle_id=circle_id,
        circle_book_id=circle_book.id,
        book_id=circle_book.book_id,
        user_id=current_user.id,
        page_number=payload.page_number,
        selected_text=payload.selected_text,
        position=payload.position,
        body=payload.body,
        visibility="circle",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    result = get_annotation(db, circle_id, row.id)
    return CircleAnnotationRead.model_validate(result)


@router.patch("/{annotation_id}", response_model=CircleAnnotationRead)
def update_annotation(
    circle_id: int,
    annotation_id: int,
    payload: CircleAnnotationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CircleAnnotationRead:
    require_member(db, circle_id, current_user.id)
    row = get_annotation(db, circle_id, annotation_id)
    if row.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own annotation")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)

    db.add(row)
    db.commit()
    db.refresh(row)
    return CircleAnnotationRead.model_validate(get_annotation(db, circle_id, row.id))


@router.delete("/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_annotation(
    circle_id: int,
    annotation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    require_member(db, circle_id, current_user.id)
    row = get_annotation(db, circle_id, annotation_id)
    if row.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own annotation")

    row.deleted_at = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
