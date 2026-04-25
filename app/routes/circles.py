from datetime import datetime, timezone
from re import sub

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.book import Book
from app.models.circle import Circle
from app.models.circle_book import CircleBook
from app.models.circle_member import CircleMember
from app.models.circle_progress_update import CircleProgressUpdate
from app.schemas.circles import CircleInviteCreate, CircleMemberRead
from app.models.user import User
from app.models.user_connection import UserConnection
from app.schemas.book import BookRead
from app.schemas.circles import (
    CircleBookCreate,
    CircleBookRead,
    CircleCreate,
    CircleInviteCreate,
    CircleMemberRead,
    CircleProgressUpdateCreate,
    CircleProgressUpdateRead,
    CircleRead,
    CircleUpdate,
)
from app.models.library_item import LibraryItem




router = APIRouter(prefix="/circles", tags=["circles"])


def slugify(value: str) -> str:
    return sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def require_circle_member(db: Session, circle_id: int, user_id: int) -> CircleMember:
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


def require_circle_admin(member: CircleMember) -> None:
    if member.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.post("/", response_model=CircleRead, status_code=201)
def create_circle(
    payload: CircleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CircleRead:
    base_slug = slugify(payload.name)
    slug = base_slug
    counter = 1

    while db.scalar(select(Circle).where(Circle.slug == slug)):
        counter += 1
        slug = f"{base_slug}-{counter}"

    circle = Circle(
        name=payload.name,
        slug=slug,
        description=payload.description,
        visibility=payload.visibility,
        owner_id=current_user.id,
    )
    db.add(circle)
    db.commit()
    db.refresh(circle)

    owner_member = CircleMember(
        circle_id=circle.id,
        user_id=current_user.id,
        role="owner",
        status="active",
    )
    db.add(owner_member)
    db.commit()

    row = db.scalar(
        select(Circle)
        .where(Circle.id == circle.id)
        .options(joinedload(Circle.owner))
    )
    if not row:
        raise HTTPException(status_code=404, detail="Circle not found after creation")

    return CircleRead.model_validate(row)


@router.get("/", response_model=list[CircleRead])
def list_my_circles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CircleRead]:
    rows = db.scalars(
        select(Circle)
        .join(CircleMember, CircleMember.circle_id == Circle.id)
        .where(
            CircleMember.user_id == current_user.id,
            CircleMember.status == "active",
            Circle.archived_at.is_(None),
        )
        .options(joinedload(Circle.owner))
    ).all()

    return [CircleRead.model_validate(row) for row in rows]


@router.get("/{circle_id}", response_model=CircleRead)
def get_circle(
    circle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CircleRead:
    require_circle_member(db, circle_id, current_user.id)

    row = db.scalar(
        select(Circle)
        .where(Circle.id == circle_id)
        .options(joinedload(Circle.owner))
    )
    if not row:
        raise HTTPException(status_code=404, detail="Circle not found")

    return CircleRead.model_validate(row)


@router.patch("/{circle_id}", response_model=CircleRead)
def update_circle(
    circle_id: int,
    payload: CircleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CircleRead:
    member = require_circle_member(db, circle_id, current_user.id)
    require_circle_admin(member)

    row = db.scalar(select(Circle).where(Circle.id == circle_id))
    if not row:
        raise HTTPException(status_code=404, detail="Circle not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(row, field, value)

    db.add(row)
    db.commit()
    db.refresh(row)

    updated = db.scalar(
        select(Circle)
        .where(Circle.id == circle_id)
        .options(joinedload(Circle.owner))
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Circle not found after update")

    return CircleRead.model_validate(updated)


@router.post("/{circle_id}/invite", response_model=CircleMemberRead, status_code=201)
def invite_circle_member(
    circle_id: int,
    payload: CircleInviteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CircleMemberRead:
    member = require_circle_member(db, circle_id, current_user.id)
    require_circle_admin(member)

    target = db.scalar(select(User).where(User.id == payload.user_id))
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.scalar(
        select(CircleMember).where(
            CircleMember.circle_id == circle_id,
            CircleMember.user_id == payload.user_id,
        )
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="User already invited or in circle",
        )

    accepted_connection = db.scalar(
        select(UserConnection).where(
            UserConnection.status == "accepted",
            or_(
                and_(
                    UserConnection.requester_id == current_user.id,
                    UserConnection.addressee_id == payload.user_id,
                ),
                and_(
                    UserConnection.requester_id == payload.user_id,
                    UserConnection.addressee_id == current_user.id,
                ),
            ),
        )
    )
    if not accepted_connection:
        raise HTTPException(
            status_code=403,
            detail="Only accepted connections can be invited into a circle.",
        )

    row = CircleMember(
        circle_id=circle_id,
        user_id=payload.user_id,
        role="member",
        status="active",
        invited_by_user_id=current_user.id,
        joined_at=datetime.now(timezone.utc),
    )

    db.add(row)
    db.commit()
    db.refresh(row)

    result = db.scalar(
        select(CircleMember)
        .where(CircleMember.id == row.id)
        .options(joinedload(CircleMember.user))
    )
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Circle member not found after invite",
        )

    return CircleMemberRead.model_validate(result)


@router.get("/{circle_id}/members", response_model=list[CircleMemberRead])
def list_circle_members(
    circle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CircleMemberRead]:
    require_circle_member(db, circle_id, current_user.id)

    rows = db.scalars(
        select(CircleMember)
        .where(CircleMember.circle_id == circle_id)
        .options(joinedload(CircleMember.user))
    ).all()

    return [CircleMemberRead.model_validate(row) for row in rows]


@router.post("/{circle_id}/books", response_model=CircleBookRead, status_code=201)
def attach_book_to_circle(
    circle_id: int,
    payload: CircleBookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CircleBookRead:
    member = require_circle_member(db, circle_id, current_user.id)
    require_circle_admin(member)

    book = db.scalar(select(Book).where(Book.id == payload.book_id))
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    existing = db.scalar(
        select(CircleBook).where(
            CircleBook.circle_id == circle_id,
            CircleBook.book_id == payload.book_id,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Book already attached to circle")

    row = CircleBook(
        circle_id=circle_id,
        book_id=payload.book_id,
        created_by_user_id=current_user.id,
        title_override=payload.title_override,
        description=payload.description,
        start_date=payload.start_date,
        target_end_date=payload.target_end_date,
        status="active",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    result = db.scalar(
        select(CircleBook)
        .where(CircleBook.id == row.id)
        .options(joinedload(CircleBook.book))
    )
    if not result:
        raise HTTPException(status_code=404, detail="Circle book not found after attach")

    return CircleBookRead(
        id=result.id,
        title_override=result.title_override,
        description=result.description,
        start_date=result.start_date,
        target_end_date=result.target_end_date,
        status=result.status,
        book=BookRead.model_validate(result.book),
    )


@router.get("/{circle_id}/books", response_model=list[CircleBookRead])
def list_circle_books(
    circle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CircleBookRead]:
    require_circle_member(db, circle_id, current_user.id)

    rows = db.scalars(
        select(CircleBook)
        .where(CircleBook.circle_id == circle_id)
        .options(joinedload(CircleBook.book))
    ).all()

    return [
        CircleBookRead(
            id=row.id,
            title_override=row.title_override,
            description=row.description,
            start_date=row.start_date,
            target_end_date=row.target_end_date,
            status=row.status,
            book=BookRead.model_validate(row.book),
        )
        for row in rows
    ]


@router.post("/{circle_id}/progress", response_model=CircleProgressUpdateRead, status_code=201)
def create_progress_update(
    circle_id: int,
    payload: CircleProgressUpdateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CircleProgressUpdateRead:
    require_circle_member(db, circle_id, current_user.id)

    library_item = db.scalar(
        select(LibraryItem).where(
            LibraryItem.id == payload.library_item_id,
            LibraryItem.user_id == current_user.id,
        )
    )
    if not library_item:
        raise HTTPException(status_code=404, detail="Library item not found")

    row = CircleProgressUpdate(
        circle_id=circle_id,
        circle_book_id=payload.circle_book_id,
        library_item_id=library_item.id,
        user_id=current_user.id,
        progress_percent=library_item.progress,
        current_page=library_item.current_page,
        bookmark_page=library_item.bookmark_page,
        note=payload.note,
        visibility=payload.visibility,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    result = db.scalar(
        select(CircleProgressUpdate)
        .where(CircleProgressUpdate.id == row.id)
        .options(joinedload(CircleProgressUpdate.user))
    )
    if not result:
        raise HTTPException(status_code=404, detail="Progress update not found after create")

    return CircleProgressUpdateRead.model_validate(result)



@router.get("/{circle_id}/progress", response_model=list[CircleProgressUpdateRead])
def list_progress_updates(
    circle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CircleProgressUpdateRead]:
    require_circle_member(db, circle_id, current_user.id)

    rows = db.scalars(
    select(CircleProgressUpdate)
    .where(CircleProgressUpdate.circle_id == circle_id)
    .options(
        joinedload(CircleProgressUpdate.user),
        joinedload(CircleProgressUpdate.circle_book).joinedload(CircleBook.book),
    )
    .order_by(CircleProgressUpdate.created_at.desc())
    ).all()

    return [CircleProgressUpdateRead.model_validate(row) for row in rows]