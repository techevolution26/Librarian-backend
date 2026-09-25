from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.book import Book
from app.models.highlight import Highlight
from app.models.note import Note
from app.models.notebook import Notebook
from app.models.quote_reference import QuoteReference
from app.models.user import User
from app.schemas.quote_reference import QuoteReferenceCreate, QuoteReferenceRead, QuoteReferenceUpdate

router = APIRouter(prefix="/quote-references", tags=["quote-references"])


def owned_reference(db: Session, reference_id: int, user_id: int) -> QuoteReference:
    row = db.scalar(select(QuoteReference).where(QuoteReference.id == reference_id, QuoteReference.user_id == user_id))
    if not row:
        raise HTTPException(status_code=404, detail="Quote reference not found")
    return row


def get_book(db: Session, book_id: int, *, active_only: bool = False) -> Book:
    query = select(Book).where(Book.id == book_id)
    if active_only:
        query = query.where(Book.archived_at.is_(None))
    book = db.scalar(query)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


def validate_note(db: Session, note_id: int | None, user_id: int, book_id: int) -> None:
    if note_id is None:
        return
    note = db.scalar(select(Note).join(Notebook).where(Note.id == note_id, Notebook.user_id == user_id))
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.book_id is not None and note.book_id != book_id:
        raise HTTPException(status_code=400, detail="Note does not belong to this book")


def validate_highlight(db: Session, highlight_id: int | None, user_id: int, book_id: int) -> Highlight | None:
    if highlight_id is None:
        return None
    highlight = db.scalar(select(Highlight).where(Highlight.id == highlight_id, Highlight.user_id == user_id))
    if not highlight:
        raise HTTPException(status_code=404, detail="Highlight not found")
    if highlight.book_id != book_id:
        raise HTTPException(status_code=400, detail="Highlight does not belong to this book")
    return highlight


def to_read(row: QuoteReference, book: Book) -> QuoteReferenceRead:
    page = f", p. {row.page_number}" if row.page_number is not None else ""
    return QuoteReferenceRead(
        id=row.id,
        user_id=row.user_id,
        book_id=row.book_id,
        highlight_id=row.highlight_id,
        note_id=row.note_id,
        page_number=row.page_number,
        locator=row.locator,
        quote_text=row.quote_text,
        citation=f"{book.title}{page} — selected passage",
        source_title=book.title,
        source_author=book.author,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/", response_model=list[QuoteReferenceRead])
def list_quote_references(
    book_id: int | None = None,
    note_id: int | None = None,
    highlight_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[QuoteReferenceRead]:
    query = select(QuoteReference).where(QuoteReference.user_id == current_user.id)
    if book_id is not None:
        query = query.where(QuoteReference.book_id == book_id)
    if note_id is not None:
        query = query.where(QuoteReference.note_id == note_id)
    if highlight_id is not None:
        query = query.where(QuoteReference.highlight_id == highlight_id)
    rows = db.scalars(query.order_by(QuoteReference.updated_at.desc(), QuoteReference.id.desc())).all()
    books = {book.id: book for book in db.scalars(select(Book).where(Book.id.in_({row.book_id for row in rows}))).all()}
    return [to_read(row, books[row.book_id]) for row in rows if row.book_id in books]


@router.get("/{reference_id}", response_model=QuoteReferenceRead)
def get_quote_reference(
    reference_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuoteReferenceRead:
    row = owned_reference(db, reference_id, current_user.id)
    return to_read(row, get_book(db, row.book_id))


@router.post("/", response_model=QuoteReferenceRead, status_code=status.HTTP_201_CREATED)
def create_quote_reference(
    payload: QuoteReferenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuoteReferenceRead:
    book = get_book(db, payload.book_id, active_only=True)
    highlight = validate_highlight(db, payload.highlight_id, current_user.id, payload.book_id)
    validate_note(db, payload.note_id, current_user.id, payload.book_id)

    page_number = payload.page_number or (highlight.page_number if highlight else None)
    locator = payload.locator or (highlight.position if highlight else None)
    quote_text = payload.quote_text
    row = QuoteReference(
        user_id=current_user.id,
        book_id=payload.book_id,
        highlight_id=payload.highlight_id,
        note_id=payload.note_id,
        page_number=page_number,
        locator=locator,
        quote_text=quote_text,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return to_read(row, book)


@router.patch("/{reference_id}", response_model=QuoteReferenceRead)
def update_quote_reference(
    reference_id: int,
    payload: QuoteReferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuoteReferenceRead:
    row = owned_reference(db, reference_id, current_user.id)
    get_book(db, row.book_id)
    data = payload.model_dump(exclude_unset=True)
    if "note_id" in data:
        validate_note(db, data["note_id"], current_user.id, row.book_id)
    for field, value in data.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return to_read(row, get_book(db, row.book_id))


@router.delete("/{reference_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quote_reference(
    reference_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    row = owned_reference(db, reference_id, current_user.id)
    db.delete(row)
    db.commit()
