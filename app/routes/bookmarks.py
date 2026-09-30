from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.book import Book
from app.models.bookmark import Bookmark
from app.models.user import User
from app.schemas.bookmark import BookmarkCreate, BookmarkRead, BookmarkUpdate
from app.services.bookmark_limits import bookmark_limit_allows_creation, get_bookmark_count
from app.services.subscription_billing import get_effective_plan, get_effective_subscription

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])


def get_owned_bookmark(db: Session, bookmark_id: int, user_id: int) -> Bookmark:
    bookmark = db.scalar(
        select(Bookmark).where(
            Bookmark.id == bookmark_id,
            Bookmark.user_id == user_id,
        )
    )
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return bookmark


@router.get("/", response_model=list[BookmarkRead])
def list_bookmarks(
    book_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BookmarkRead]:
    query = select(Bookmark).where(Bookmark.user_id == current_user.id)
    if book_id is not None:
        query = query.where(Bookmark.book_id == book_id)

    rows = db.scalars(
        query.order_by(Bookmark.page_number.asc().nulls_last(), Bookmark.created_at.asc(), Bookmark.id.asc())
    ).all()
    return [BookmarkRead.model_validate(row) for row in rows]


@router.get("/usage")
def bookmark_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    """Return current bookmark usage without assuming a subscription plan."""
    return {"count": get_bookmark_count(db, user_id=current_user.id)}


@router.get("/{bookmark_id}", response_model=BookmarkRead)
def get_bookmark(
    bookmark_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookmarkRead:
    return BookmarkRead.model_validate(get_owned_bookmark(db, bookmark_id, current_user.id))


@router.post("/", response_model=BookmarkRead, status_code=status.HTTP_201_CREATED)
def create_bookmark(
    payload: BookmarkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookmarkRead:
    book = db.scalar(
        select(Book).where(
            Book.id == payload.book_id,
            Book.archived_at.is_(None),
            Book.visibility == "published",
        )
    )
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Serialize per-user creation against concurrent requests so a finite
    # bookmark ceiling cannot be exceeded by two simultaneous inserts.
    db.execute(select(User).where(User.id == current_user.id).with_for_update())

    effective_subscription = get_effective_subscription(db, current_user.id)
    effective_plan = None if effective_subscription is not None else get_effective_plan(db, current_user.id)
    effective_plan_id = effective_subscription.plan_id if effective_subscription is not None else (effective_plan.id if effective_plan else None)
    if effective_plan_id is not None:
        allowed, current_count, limit = bookmark_limit_allows_creation(
            db,
            user_id=current_user.id,
            plan_id=effective_plan_id,
        )
        if not allowed:
            detail = (
                "Bookmark limit reached"
                if limit is not None
                else "Bookmarks are not enabled for your current plan"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "bookmark_limit_reached",
                    "message": detail,
                    "count": current_count,
                    "limit": limit,
                },
            )

    bookmark = Bookmark(
        user_id=current_user.id,
        book_id=payload.book_id,
        page_number=payload.page_number,
        position=payload.position,
        title=payload.title or "Bookmark",
        note=payload.note,
        color=payload.color,
    )
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    return BookmarkRead.model_validate(bookmark)


@router.patch("/{bookmark_id}", response_model=BookmarkRead)
def update_bookmark(
    bookmark_id: int,
    payload: BookmarkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookmarkRead:
    bookmark = get_owned_bookmark(db, bookmark_id, current_user.id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(bookmark, field, value)

    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    return BookmarkRead.model_validate(bookmark)


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark(
    bookmark_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    bookmark = get_owned_bookmark(db, bookmark_id, current_user.id)
    db.delete(bookmark)
    db.commit()
