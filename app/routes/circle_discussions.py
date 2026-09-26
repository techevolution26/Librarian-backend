from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.circle_book import CircleBook
from app.models.circle_discussion import CircleDiscussion, CircleDiscussionReply
from app.models.circle_member import CircleMember
from app.models.user import User
from app.schemas.circle_discussions import (
    CircleDiscussionCreate,
    CircleDiscussionDetailRead,
    CircleDiscussionRead,
    CircleDiscussionReplyCreate,
    CircleDiscussionReplyRead,
    CircleDiscussionReplyUpdate,
    CircleDiscussionUpdate,
)

router = APIRouter(prefix="/circles/{circle_id}/discussions", tags=["circle discussions"])


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


def get_circle_book(db: Session, circle_id: int, circle_book_id: int) -> CircleBook:
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


def get_discussion(db: Session, circle_id: int, discussion_id: int) -> CircleDiscussion:
    row = db.scalar(
        select(CircleDiscussion)
        .where(
            CircleDiscussion.id == discussion_id,
            CircleDiscussion.circle_id == circle_id,
            CircleDiscussion.deleted_at.is_(None),
        )
        .options(joinedload(CircleDiscussion.user))
    )
    if not row:
        raise HTTPException(status_code=404, detail="Discussion not found")
    return row


def discussion_read(db: Session, row: CircleDiscussion) -> CircleDiscussionRead:
    count = db.scalar(
        select(func.count(CircleDiscussionReply.id)).where(
            CircleDiscussionReply.discussion_id == row.id,
            CircleDiscussionReply.deleted_at.is_(None),
        )
    ) or 0
    return CircleDiscussionRead.model_validate({
        **row.__dict__,
        "replies_count": count,
        "user": row.user,
    })


def reply_read(row: CircleDiscussionReply) -> CircleDiscussionReplyRead:
    return CircleDiscussionReplyRead.model_validate(row)


@router.get("/", response_model=list[CircleDiscussionRead])
def list_discussions(
    circle_id: int,
    circle_book_id: int | None = None,
    page_number: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CircleDiscussionRead]:
    require_member(db, circle_id, current_user.id)
    query = (
        select(CircleDiscussion)
        .where(
            CircleDiscussion.circle_id == circle_id,
            CircleDiscussion.deleted_at.is_(None),
        )
        .options(joinedload(CircleDiscussion.user))
    )
    if circle_book_id is not None:
        query = query.where(CircleDiscussion.circle_book_id == circle_book_id)
    if page_number is not None:
        query = query.where(CircleDiscussion.page_number == page_number)

    rows = db.scalars(query.order_by(CircleDiscussion.created_at.desc(), CircleDiscussion.id.desc())).all()
    return [discussion_read(db, row) for row in rows]


@router.post("/", response_model=CircleDiscussionRead, status_code=status.HTTP_201_CREATED)
def create_discussion(
    circle_id: int,
    payload: CircleDiscussionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CircleDiscussionRead:
    require_member(db, circle_id, current_user.id)
    circle_book = get_circle_book(db, circle_id, payload.circle_book_id)
    row = CircleDiscussion(
        circle_id=circle_id,
        circle_book_id=circle_book.id,
        book_id=circle_book.book_id,
        user_id=current_user.id,
        page_number=payload.page_number,
        body=payload.body,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    row = get_discussion(db, circle_id, row.id)
    return discussion_read(db, row)


@router.get("/{discussion_id}", response_model=CircleDiscussionDetailRead)
def get_discussion_detail(
    circle_id: int,
    discussion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CircleDiscussionDetailRead:
    require_member(db, circle_id, current_user.id)
    row = get_discussion(db, circle_id, discussion_id)
    replies = db.scalars(
        select(CircleDiscussionReply)
        .where(
            CircleDiscussionReply.discussion_id == row.id,
            CircleDiscussionReply.circle_id == circle_id,
            CircleDiscussionReply.deleted_at.is_(None),
        )
        .options(joinedload(CircleDiscussionReply.user))
        .order_by(CircleDiscussionReply.created_at.asc(), CircleDiscussionReply.id.asc())
    ).all()
    base = discussion_read(db, row)
    return CircleDiscussionDetailRead.model_validate({
        **base.model_dump(),
        "replies": [reply_read(reply).model_dump() for reply in replies],
    })


@router.patch("/{discussion_id}", response_model=CircleDiscussionRead)
def update_discussion(
    circle_id: int,
    discussion_id: int,
    payload: CircleDiscussionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CircleDiscussionRead:
    require_member(db, circle_id, current_user.id)
    row = get_discussion(db, circle_id, discussion_id)
    if row.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own discussion")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.add(row)
    db.commit()
    db.refresh(row)
    return discussion_read(db, get_discussion(db, circle_id, row.id))


@router.delete("/{discussion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_discussion(
    circle_id: int,
    discussion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    require_member(db, circle_id, current_user.id)
    row = get_discussion(db, circle_id, discussion_id)
    if row.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own discussion")
    row.deleted_at = datetime.now(timezone.utc)
    db.add(row)
    db.commit()


@router.post("/{discussion_id}/replies", response_model=CircleDiscussionReplyRead, status_code=status.HTTP_201_CREATED)
def create_reply(
    circle_id: int,
    discussion_id: int,
    payload: CircleDiscussionReplyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CircleDiscussionReplyRead:
    require_member(db, circle_id, current_user.id)
    get_discussion(db, circle_id, discussion_id)
    row = CircleDiscussionReply(
        discussion_id=discussion_id,
        circle_id=circle_id,
        user_id=current_user.id,
        body=payload.body,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    row = db.scalar(
        select(CircleDiscussionReply)
        .where(CircleDiscussionReply.id == row.id)
        .options(joinedload(CircleDiscussionReply.user))
    )
    return reply_read(row)


def get_reply(db: Session, circle_id: int, reply_id: int) -> CircleDiscussionReply:
    row = db.scalar(
        select(CircleDiscussionReply)
        .where(
            CircleDiscussionReply.id == reply_id,
            CircleDiscussionReply.circle_id == circle_id,
            CircleDiscussionReply.deleted_at.is_(None),
        )
        .options(joinedload(CircleDiscussionReply.user))
    )
    if not row:
        raise HTTPException(status_code=404, detail="Discussion reply not found")
    return row


@router.patch("/{discussion_id}/replies/{reply_id}", response_model=CircleDiscussionReplyRead)
def update_reply(
    circle_id: int,
    discussion_id: int,
    reply_id: int,
    payload: CircleDiscussionReplyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CircleDiscussionReplyRead:
    require_member(db, circle_id, current_user.id)
    get_discussion(db, circle_id, discussion_id)
    row = get_reply(db, circle_id, reply_id)
    if row.discussion_id != discussion_id:
        raise HTTPException(status_code=404, detail="Discussion reply not found")
    if row.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own reply")
    row.body = payload.body
    db.add(row)
    db.commit()
    return reply_read(get_reply(db, circle_id, row.id))


@router.delete("/{discussion_id}/replies/{reply_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reply(
    circle_id: int,
    discussion_id: int,
    reply_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    require_member(db, circle_id, current_user.id)
    get_discussion(db, circle_id, discussion_id)
    row = get_reply(db, circle_id, reply_id)
    if row.discussion_id != discussion_id:
        raise HTTPException(status_code=404, detail="Discussion reply not found")
    if row.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own reply")
    row.deleted_at = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
