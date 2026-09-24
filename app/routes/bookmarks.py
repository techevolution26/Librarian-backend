from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.book import Book
from app.models.bookmark import Bookmark
from app.models.user import User
from app.schemas.bookmark import BookmarkCreate, BookmarkRead, BookmarkUpdate

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
        query.order_by(
            Bookmark.page_number.asc().nulls_last(),
            Bookmark.created_at.asc(),
            Bookmark.id.asc(),
        )
    ).all()
    return [BookmarkRead.model_validate(row) for row in rows]


@router.get("/{bookmark_id}", response_model=BookmarkRead)
def get_bookmark(
    bookmark_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookmarkRead:
    return BookmarkRead.model_validate(
        get_owned_bookmark(db, bookmark_id, current_user.id)
    )


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
