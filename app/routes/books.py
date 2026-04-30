import os
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile ,Query
from sqlalchemy import select, case, func ,or_
from sqlalchemy.orm import Session
from app.models.library_item import LibraryItem
from app.core.database import get_db
from app.core.storage import BOOKS_STORAGE_DIR, build_public_file_url, ensure_storage_dirs
from app.models.book import Book
from app.schemas.book import BookContentRead, BookRead

router = APIRouter(prefix="/books", tags=["books"])

ensure_storage_dirs()


def to_book_read(row: Book) -> BookRead:
    
    return BookRead(
        id=row.id,
        title=row.title,
        author=row.author,
        cover=row.cover,
        description=row.description,
        rating=row.rating,
        pages=row.pages,
        genre=row.genres,
        source_type=row.source_type,
        source_url=row.source_url,
        mime_type=row.mime_type,
    )


@router.get("/", response_model=list[BookRead])
def list_books(db: Session = Depends(get_db)) -> list[BookRead]:
    rows = db.scalars(select(Book).order_by(Book.id)).all()
    return [to_book_read(row) for row in rows]


@router.get("/featured", response_model=BookRead)
def get_featured_book(db: Session = Depends(get_db)) -> BookRead:
    since = datetime.now(timezone.utc) - timedelta(days=30)

    featured_score = (
        func.coalesce(func.avg(Book.rating), 0) * 2
        + func.coalesce(func.count(LibraryItem.id), 0)
        + func.coalesce(
            func.sum(
                case(
                    (LibraryItem.status == "reading", 5),
                    (LibraryItem.status == "saved", 3),
                    (LibraryItem.status == "finished", 4),
                    else_=1,
                )
            ),
            0,
        )
    ).label("featured_score")

    row = db.scalar(
        select(Book)
        .outerjoin(
            LibraryItem,
            (LibraryItem.book_id == Book.id)
            & (LibraryItem.updated_at >= since),
        )
        .group_by(Book.id)
        .order_by(
            featured_score.desc(),
            Book.rating.desc(),
            Book.pages.desc(),
            Book.id.desc(),
        )
        .limit(1)
    )

    if not row:
        raise HTTPException(status_code=404, detail="No featured book found")

    return to_book_read(row)

@router.get("/trending", response_model=list[BookRead])
def list_trending_books(
    limit: int = 12,
    db: Session = Depends(get_db),
) -> list[BookRead]:
    since = datetime.now(timezone.utc) - timedelta(days=14)

    trending_score = (
        func.count(LibraryItem.id) * 2
        + func.sum(
            case(
                (LibraryItem.status == "reading", 5),
                (LibraryItem.status == "saved", 3),
                (LibraryItem.status == "finished", 4),
                else_=1,
            )
        )
        + func.coalesce(func.avg(Book.rating), 0)
    ).label("trending_score")

    rows = db.scalars(
        select(Book)
        .outerjoin(
            LibraryItem,
            (LibraryItem.book_id == Book.id)
            & (LibraryItem.updated_at >= since),
        )
        .group_by(Book.id)
        .order_by(trending_score.desc(), Book.rating.desc(), Book.id.desc())
        .limit(limit)
    ).all()

    return [to_book_read(row) for row in rows]

@router.get("/genres", response_model=list[str])
def list_book_genres(db: Session = Depends(get_db)) -> list[str]:
    rows = db.scalars(select(Book)).all()

    genres: set[str] = set()
    for book in rows:
        for genre in book.genres:
            genres.add(genre)

    return ["All", *sorted(genres)]



@router.get("/discover", response_model=list[BookRead])
def discover_books(
    q: str | None = None,
    genre: str = "All",
    sort: str = "recommended",
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[BookRead]:
    stmt = select(Book)

    if q:
        pattern = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Book.title).like(pattern),
                func.lower(Book.author).like(pattern),
                func.lower(Book.description).like(pattern),
            )
        )

    rows = db.scalars(stmt).all()

    if genre and genre.lower() != "all":
        rows = [
            book
            for book in rows
            if genre.lower() in [item.lower() for item in book.genres]
        ]

    if sort == "top-rated":
        rows.sort(key=lambda book: (book.rating, book.id), reverse=True)
    elif sort == "newest":
        rows.sort(key=lambda book: book.id, reverse=True)
    else:
        rows.sort(key=lambda book: (book.rating, book.id), reverse=True)

    rows = rows[offset : offset + limit]

    return [to_book_read(row) for row in rows]


@router.get("/discover/stats")
def discover_stats(
    q: str | None = None,
    genre: str = "All",
    db: Session = Depends(get_db),
) -> dict[str, int]:
    rows = discover_books(q=q, genre=genre, sort="recommended", limit=100, offset=0, db=db)

    categories = {
        genre_item
        for book in rows
        for genre_item in book.genre
    }

    return {
        "visible_books": len(rows),
        "top_rated": len([book for book in rows if book.rating >= 4.5]),
        "new_this_week": min(len(rows), 6),
        "categories": len(categories),
    }

@router.get("/{book_id}", response_model=BookRead)
def get_book(book_id: int, db: Session = Depends(get_db)) -> BookRead:
    row = db.scalar(select(Book).where(Book.id == book_id))
    if not row:
        raise HTTPException(status_code=404, detail="Book not found")
    return to_book_read(row)


@router.get("/{book_id}/content", response_model=BookContentRead)
def get_book_content(book_id: int, db: Session = Depends(get_db)) -> BookContentRead:
    row = db.scalar(select(Book).where(Book.id == book_id))
    if not row:
        raise HTTPException(status_code=404, detail="Book not found")

    return BookContentRead(
        id=row.id,
        title=row.title,
        source_type=row.source_type,
        mime_type=row.mime_type,
        source_url=row.source_url,
        content_text=row.content_text,
    )


@router.post("/upload-pdf", response_model=BookRead, status_code=201)
async def upload_pdf_book(
    request: Request,
    title: str = Form(...),
    author: str = Form(...),
    cover: str = Form("/book-placeholder.jpg"),
    description: str = Form(...),
    rating: float = Form(0),
    pages: int = Form(0),
    genre_csv: str = Form(""),
    pdf_file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> BookRead:
    if pdf_file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")

    suffix = Path(pdf_file.filename or "book.pdf").suffix or ".pdf"
    filename = f"{uuid4().hex}{suffix}"
    destination = BOOKS_STORAGE_DIR / filename

    file_bytes = await pdf_file.read()
    destination.write_bytes(file_bytes)

    source_url = build_public_file_url(str(request.base_url), "books", filename)

    book = Book(
        title=title,
        author=author,
        cover=cover,
        description=description,
        rating=rating,
        pages=pages,
        source_type="pdf",
        source_url=source_url,
        source_path=str(destination),
        mime_type="application/pdf",
        content_text=None,
    )
    book.genres = [g.strip() for g in genre_csv.split(",") if g.strip()]

    db.add(book)
    db.commit()
    db.refresh(book)

    return to_book_read(book)


@router.patch("/{book_id}/update-pdf", response_model=BookRead)
async def update_book_pdf_only(
    request: Request,
    book_id: int,
    pdf_file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> BookRead:
    if pdf_file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")

    book = db.scalar(select(Book).where(Book.id == book_id))
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.source_path and os.path.exists(book.source_path):
        try:
            os.remove(book.source_path)
        except OSError:
            pass

    suffix = Path(pdf_file.filename or "book.pdf").suffix or ".pdf"
    filename = f"{uuid4().hex}{suffix}"
    destination = BOOKS_STORAGE_DIR / filename

    file_bytes = await pdf_file.read()
    destination.write_bytes(file_bytes)

    source_url = build_public_file_url(str(request.base_url), "books", filename)

    book.source_type = "pdf"
    book.source_url = source_url
    book.source_path = str(destination)
    book.mime_type = "application/pdf"
    book.content_text = None

    db.add(book)
    db.commit()
    db.refresh(book)

    return to_book_read(book)