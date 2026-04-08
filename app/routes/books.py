import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

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