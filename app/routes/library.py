from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.book import Book
from app.models.library_item import LibraryItem
from app.models.user import User
from app.schemas.book import BookRead
from app.schemas.library import (
    LibraryItemRead,
    LibraryMutationCreate,
    LibrarySummary,
    PdfProgressUpdate,
    StartReadingPayload,
)

router = APIRouter(prefix="/library", tags=["library"])


def get_default_user(db: Session) -> User:
    user = db.scalar(select(User).order_by(User.id))
    if not user:
        raise HTTPException(status_code=404, detail="No user found")
    return user


def to_library_item_read(row: LibraryItem) -> LibraryItemRead:
    return LibraryItemRead(
        id=row.id,
        status=row.status,
        progress=row.progress,
        current_page=row.current_page,
        total_pages=row.total_pages,
        bookmark_page=row.bookmark_page,
        last_read_at=row.last_read_at,
        saved_at=row.saved_at,
        finished_at=row.finished_at,
        updated_at=row.updated_at,
        book=BookRead(
            id=row.book.id,
            title=row.book.title,
            author=row.book.author,
            cover=row.book.cover,
            description=row.book.description,
            rating=row.book.rating,
            pages=row.book.pages,
            genre=row.book.genres,
            source_type=row.book.source_type,
            source_url=row.book.source_url,
            mime_type=row.book.mime_type,
        ),
    )


@router.get("/", response_model=list[LibraryItemRead])
def list_library_items(db: Session = Depends(get_db)) -> list[LibraryItemRead]:
    user = get_default_user(db)

    rows = db.scalars(
        select(LibraryItem)
        .where(LibraryItem.user_id == user.id)
        .options(joinedload(LibraryItem.book))
        .order_by(LibraryItem.updated_at.desc(), LibraryItem.id.desc())
    ).all()

    return [to_library_item_read(row) for row in rows]


@router.get("/summary", response_model=LibrarySummary)
def get_library_summary(db: Session = Depends(get_db)) -> LibrarySummary:
    user = get_default_user(db)

    rows = db.scalars(
        select(LibraryItem)
        .where(LibraryItem.user_id == user.id)
        .options(joinedload(LibraryItem.book))
    ).all()

    all_count = len(rows)
    reading_count = sum(1 for row in rows if row.status == "reading")
    saved_count = sum(1 for row in rows if row.status == "saved")
    finished_count = sum(1 for row in rows if row.status == "finished")

    average_rating = (
        round(sum(row.book.rating for row in rows) / all_count, 1)
        if all_count > 0
        else 0.0
    )

    return LibrarySummary(
        all=all_count,
        reading=reading_count,
        saved=saved_count,
        finished=finished_count,
        average_rating=average_rating,
    )


@router.post("/", response_model=LibraryItemRead, status_code=201)
def add_to_library(
    payload: LibraryMutationCreate,
    db: Session = Depends(get_db),
) -> LibraryItemRead:
    user = get_default_user(db)

    book = db.scalar(select(Book).where(Book.id == payload.book_id))
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    existing = db.scalar(
        select(LibraryItem)
        .where(LibraryItem.user_id == user.id, LibraryItem.book_id == payload.book_id)
        .options(joinedload(LibraryItem.book))
    )

    if existing:
        existing.status = payload.status
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return to_library_item_read(existing)

    item = LibraryItem(
        user_id=user.id,
        book_id=payload.book_id,
        status=payload.status,
        progress=0,
    )
    db.add(item)
    db.commit()

    row = db.scalar(
        select(LibraryItem)
        .where(LibraryItem.id == item.id)
        .options(joinedload(LibraryItem.book))
    )
    return to_library_item_read(row)


@router.patch("/start-reading", response_model=LibraryItemRead)
def start_reading(
    payload: StartReadingPayload,
    db: Session = Depends(get_db),
) -> LibraryItemRead:
    user = get_default_user(db)

    item = db.scalar(
        select(LibraryItem)
        .where(LibraryItem.user_id == user.id, LibraryItem.book_id == payload.book_id)
        .options(joinedload(LibraryItem.book))
    )

    if not item:
        item = LibraryItem(
            user_id=user.id,
            book_id=payload.book_id,
            status="reading",
            progress=0,
            current_page=1,
            last_read_at=datetime.now(timezone.utc),
        )
        db.add(item)
        db.commit()
        row = db.scalar(
            select(LibraryItem)
            .where(LibraryItem.id == item.id)
            .options(joinedload(LibraryItem.book))
        )
        return to_library_item_read(row)

    item.status = "reading"
    item.current_page = item.current_page or 1
    item.last_read_at = datetime.now(timezone.utc)

    db.add(item)
    db.commit()
    db.refresh(item)
    return to_library_item_read(item)


@router.patch("/{book_id}/pdf-progress", response_model=LibraryItemRead)
def save_pdf_progress(
    book_id: int,
    payload: PdfProgressUpdate,
    db: Session = Depends(get_db),
) -> LibraryItemRead:
    user = get_default_user(db)

    item = db.scalar(
        select(LibraryItem)
        .where(LibraryItem.user_id == user.id, LibraryItem.book_id == book_id)
        .options(joinedload(LibraryItem.book))
    )

    if not item:
        raise HTTPException(status_code=404, detail="Library item not found")

    item.status = "reading"
    item.current_page = payload.current_page
    item.total_pages = payload.total_pages
    item.bookmark_page = payload.bookmark_page
    item.progress = payload.progress
    item.last_read_at = datetime.now(timezone.utc)

    if payload.progress >= 100:
        item.status = "finished"
        item.finished_at = datetime.now(timezone.utc)

    db.add(item)
    db.commit()
    db.refresh(item)

    return to_library_item_read(item)


@router.get("/{book_id}", response_model=LibraryItemRead)
def get_library_item_for_book(
    book_id: int,
    db: Session = Depends(get_db),
) -> LibraryItemRead:
    user = get_default_user(db)

    item = db.scalar(
        select(LibraryItem)
        .where(LibraryItem.user_id == user.id, LibraryItem.book_id == book_id)
        .options(joinedload(LibraryItem.book))
    )

    if not item:
        raise HTTPException(status_code=404, detail="Library item not found")

    return to_library_item_read(item)