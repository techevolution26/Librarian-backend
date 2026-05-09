import os
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile ,Query
from sqlalchemy import select, case, func ,or_
from sqlalchemy.orm import Session
from app.models.library_item import LibraryItem
from app.core.database import get_db
from app.core.storage import BOOKS_STORAGE_DIR, COVERS_STORAGE_DIR, build_public_file_url, ensure_storage_dirs
from app.models.book import Book
from app.schemas.book import BookContentRead, BookRead
from app.models.user import User
from app.core.authz import require_admin_user
from app.core.security import get_current_user

from app.services.admin_activity import log_admin_activity
from app.models.admin_activity_log import AdminActivityLog

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
        visibility=getattr(row, "visibility", "published"),
        archived_at=getattr(row, "archived_at", None),
        is_featured=getattr(row, "is_featured", False),
    )

def public_books_stmt():
    return (
        select(Book)
        .where(Book.archived_at.is_(None))
        .where(Book.visibility == "published")
    )



@router.get("/admin/list", response_model=list[BookRead])
def admin_list_books(
    include_archived: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BookRead]:
    require_admin_user(current_user)

    stmt = select(Book).order_by(Book.id.desc())

    if not include_archived:
        stmt = stmt.where(Book.archived_at.is_(None))

    rows = db.scalars(stmt).all()
    return [to_book_read(row) for row in rows]


@router.get("/admin/activity")
def list_admin_activity(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin_user(current_user)

    rows = db.scalars(
        select(AdminActivityLog)
        .order_by(AdminActivityLog.created_at.desc(), AdminActivityLog.id.desc())
        .limit(limit)
    ).all()

    return [
        {
            "id": row.id,
            "admin_user_id": row.admin_user_id,
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "metadata": row.metadata_json,
            "created_at": row.created_at,
        }
        for row in rows
    ]



@router.get("/admin/{book_id}", response_model=BookRead)
def admin_get_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookRead:
    require_admin_user(current_user)

    row = db.scalar(select(Book).where(Book.id == book_id))

    if not row:
        raise HTTPException(status_code=404, detail="Book not found")

    return to_book_read(row)



@router.get("/featured", response_model=BookRead)
def get_featured_book(db: Session = Depends(get_db)) -> BookRead:
    manual_featured = db.scalar(
        public_books_stmt()
        .where(Book.is_featured.is_(True))
        .order_by(Book.id.desc())
        .limit(1)
    )

    if manual_featured:
        return to_book_read(manual_featured)

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
        public_books_stmt()
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
        + func.coalesce(func.avg(Book.rating), 0)
    ).label("trending_score")

    rows = db.scalars(
        public_books_stmt()
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


@router.get("/discover", response_model=list[BookRead])
def discover_books(
    q: str | None = None,
    genre: str = "All",
    sort: str = "recommended",
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[BookRead]:
    stmt = public_books_stmt()

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
            if any(item.lower() == genre.lower() for item in book.genres)
        ]

    if sort == "top-rated":
        rows.sort(key=lambda book: (book.rating or 0, book.id), reverse=True)
    elif sort == "newest":
        rows.sort(key=lambda book: book.id, reverse=True)
    elif sort == "featured":
        rows.sort(
            key=lambda book: (
                1 if getattr(book, "is_featured", False) else 0,
                book.rating or 0,
                book.id,
            ),
            reverse=True,
        )
    else:
        rows.sort(key=lambda book: (book.rating or 0, book.id), reverse=True)

    rows = rows[offset : offset + limit]

    return [to_book_read(row) for row in rows]



@router.get("/genres", response_model=list[str])
def list_book_genres(db: Session = Depends(get_db)) -> list[str]:
    rows = db.scalars(select(Book)).all()

    genres: set[str] = set()
    for book in rows:
        for genre in book.genres:
            genres.add(genre)

    return ["All", *sorted(genres)]


@router.get("/", response_model=list[BookRead])
def list_books(db: Session = Depends(get_db)) -> list[BookRead]:
    rows = db.scalars(
        public_books_stmt().order_by(Book.id.desc())
    ).all()

    return [to_book_read(row) for row in rows]


@router.get("/{book_id}", response_model=BookRead)
def get_book(book_id: int, db: Session = Depends(get_db)) -> BookRead:
    row = db.scalar(
        public_books_stmt().where(Book.id == book_id)
    )

    if not row:
        raise HTTPException(status_code=404, detail="Book not found")

    return to_book_read(row)


@router.patch("/{book_id}/feature", response_model=BookRead)
def set_featured_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookRead:
    require_admin_user(current_user)

    book = db.scalar(select(Book).where(Book.id == book_id))

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.archived_at is not None:
        raise HTTPException(status_code=400, detail="Archived books cannot be featured")

    if book.visibility != "published":
        raise HTTPException(status_code=400, detail="Only published books can be featured")

    db.query(Book).update({Book.is_featured: False})
    book.is_featured = True

    log_admin_activity(
        db,
        current_user,
        action="book.featured",
        entity_type="book",
        entity_id=book.id,
        metadata={"title": book.title},
    )

    db.commit()
    db.refresh(book)

    return to_book_read(book)


@router.patch("/{book_id}/unfeature", response_model=BookRead)
def unset_featured_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookRead:
    require_admin_user(current_user)

    book = db.scalar(select(Book).where(Book.id == book_id))

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    book.is_featured = False

    log_admin_activity(
        db,
        current_user,
        action="book.unfeatured",
        entity_type="book",
        entity_id=book.id,
        metadata={"title": book.title},
    )

    db.commit()
    db.refresh(book)

    return to_book_read(book)


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
    current_user: User = Depends(get_current_user),
) -> BookRead:
    require_admin_user(current_user)

    if pdf_file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")

    suffix = Path(pdf_file.filename or "book.pdf").suffix or ".pdf"
    filename = f"{uuid4().hex}{suffix}"
    destination = BOOKS_STORAGE_DIR / filename

    file_bytes = await pdf_file.read()

    max_pdf_size = 25 * 1024 * 1024
    if len(file_bytes) > max_pdf_size:
        raise HTTPException(status_code=413, detail="PDF file is too large")

    destination.write_bytes(file_bytes)

    source_url = str(request.base_url).rstrip("/") + f"/static/books/{filename}"

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
    current_user: User = Depends(get_current_user),
) -> BookRead:
    require_admin_user(current_user)

    if pdf_file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")

    book = db.scalar(select(Book).where(Book.id == book_id))

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    suffix = Path(pdf_file.filename or "book.pdf").suffix or ".pdf"
    filename = f"{uuid4().hex}{suffix}"
    destination = BOOKS_STORAGE_DIR / filename

    file_bytes = await pdf_file.read()

    max_pdf_size = 25 * 1024 * 1024
    if len(file_bytes) > max_pdf_size:
        raise HTTPException(status_code=413, detail="PDF file is too large")

    if book.source_path and os.path.exists(book.source_path):
        try:
            os.remove(book.source_path)
        except OSError:
            pass

    destination.write_bytes(file_bytes)

    source_url = str(request.base_url).rstrip("/") + f"/static/books/{filename}"

    book.source_type = "pdf"
    book.source_url = source_url
    book.source_path = str(destination)
    book.mime_type = "application/pdf"

    log_admin_activity(
        db,
        current_user,
        action="book.pdf_replaced",
        entity_type="book",
        entity_id=book.id,
        metadata={"filename": filename},
    )

    db.commit()
    db.refresh(book)

    return to_book_read(book)




@router.patch("/{book_id}", response_model=BookRead)
def update_book_metadata(
    book_id: int,
    title: str | None = Form(None),
    author: str | None = Form(None),
    cover: str | None = Form(None),
    description: str | None = Form(None),
    rating: float | None = Form(None),
    pages: int | None = Form(None),
    genre_csv: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookRead:
    require_admin_user(current_user)

    book = db.scalar(select(Book).where(Book.id == book_id))
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if title is not None:
        book.title = title
    if author is not None:
        book.author = author
    if cover is not None:
        book.cover = cover
    if description is not None:
        book.description = description
    if rating is not None:
        book.rating = rating
    if pages is not None:
        book.pages = pages
    if genre_csv is not None:
        book.genres = [g.strip() for g in genre_csv.split(",") if g.strip()]

    db.commit()
    db.refresh(book)

    return to_book_read(book)


@router.patch("/{book_id}", response_model=BookRead)
def update_book_metadata(
    book_id: int,
    title: str | None = Form(None),
    author: str | None = Form(None),
    cover: str | None = Form(None),
    description: str | None = Form(None),
    rating: float | None = Form(None),
    pages: int | None = Form(None),
    genre_csv: str | None = Form(None),
    visibility: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookRead:
    require_admin_user(current_user)

    book = db.scalar(select(Book).where(Book.id == book_id))

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if visibility is not None and visibility not in {"draft", "published"}:
        raise HTTPException(status_code=400, detail="Invalid visibility")

    if title is not None:
        book.title = title
    if author is not None:
        book.author = author
    if cover is not None:
        book.cover = cover
    if description is not None:
        book.description = description
    if rating is not None:
        book.rating = rating
    if pages is not None:
        book.pages = pages
    if genre_csv is not None:
        book.genres = [g.strip() for g in genre_csv.split(",") if g.strip()]
    if visibility is not None:
        book.visibility = visibility

    log_admin_activity(
        db,
        current_user,
        action="book.metadata_updated",
        entity_type="book",
        entity_id=book.id,
        metadata={"title": book.title},
    )

    db.commit()
    db.refresh(book)

    return to_book_read(book)




@router.post("/{book_id}/cover", response_model=BookRead)
async def upload_book_cover(
    request: Request,
    book_id: int,
    cover_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookRead:
    require_admin_user(current_user)

    if cover_file.content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise HTTPException(
            status_code=400,
            detail="Cover must be PNG, JPEG, or WEBP",
        )

    book = db.scalar(select(Book).where(Book.id == book_id))

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    suffix = Path(cover_file.filename or "cover").suffix or ".jpg"
    filename = f"{uuid4().hex}{suffix}"
    destination = COVERS_STORAGE_DIR / filename

    file_bytes = await cover_file.read()

    max_cover_size = 5 * 1024 * 1024
    if len(file_bytes) > max_cover_size:
        raise HTTPException(status_code=413, detail="Cover image is too large")

    destination.write_bytes(file_bytes)

    cover_url = str(request.base_url).rstrip("/") + f"/static/covers/{filename}"

    book.cover = cover_url
    book.cover_path = str(destination)

    log_admin_activity(
        db,
        current_user,
        action="book.cover_uploaded",
        entity_type="book",
        entity_id=book.id,
        metadata={"filename": filename},
    )

    db.commit()
    db.refresh(book)

    return to_book_read(book)



@router.patch("/{book_id}/archive", response_model=BookRead)
def archive_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookRead:
    require_admin_user(current_user)

    book = db.scalar(select(Book).where(Book.id == book_id))

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    book.archived_at = datetime.now(timezone.utc)

    log_admin_activity(
        db,
        current_user,
        action="book.archived",
        entity_type="book",
        entity_id=book.id,
        metadata={"title": book.title},
    )

    db.commit()
    db.refresh(book)

    return to_book_read(book)



@router.patch("/{book_id}/restore", response_model=BookRead)
def restore_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookRead:
    require_admin_user(current_user)

    book = db.scalar(select(Book).where(Book.id == book_id))

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    book.archived_at = None

    log_admin_activity(
        db,
        current_user,
        action="book.restored",
        entity_type="book",
        entity_id=book.id,
        metadata={"title": book.title},
    )

    db.commit()
    db.refresh(book)

    return to_book_read(book)


@router.delete("/{book_id}", status_code=204)
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    require_admin_user(current_user)

    book = db.scalar(select(Book).where(Book.id == book_id))

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    title = book.title

    if book.source_path and os.path.exists(book.source_path):
        try:
            os.remove(book.source_path)
        except OSError:
            pass

    if getattr(book, "cover_path", None) and os.path.exists(book.cover_path):
        try:
            os.remove(book.cover_path)
        except OSError:
            pass

    db.delete(book)

    log_admin_activity(
        db,
        current_user,
        action="book.deleted",
        entity_type="book",
        entity_id=book_id,
        metadata={"title": title},
    )

    db.commit()
