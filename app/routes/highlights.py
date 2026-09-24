from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.book import Book
from app.models.highlight import Highlight
from app.models.note import Note
from app.models.notebook import Notebook
from app.models.user import User
from app.schemas.highlight import HighlightCreate, HighlightRead, HighlightUpdate

router = APIRouter(prefix="/highlights", tags=["highlights"])


def owned_highlight(db: Session, highlight_id: int, user_id: int) -> Highlight:
    row = db.scalar(select(Highlight).where(Highlight.id == highlight_id, Highlight.user_id == user_id))
    if not row:
        raise HTTPException(status_code=404, detail="Highlight not found")
    return row


def validate_book(db: Session, book_id: int) -> None:
    book = db.scalar(select(Book).where(Book.id == book_id, Book.archived_at.is_(None)))
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")


def validate_note(db: Session, note_id: int | None, user_id: int, book_id: int) -> None:
    if note_id is None:
        return
    note = db.scalar(select(Note).join(Notebook).where(Note.id == note_id, Notebook.user_id == user_id))
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.book_id is not None and note.book_id != book_id:
        raise HTTPException(status_code=400, detail="Note does not belong to this book")


@router.get("/", response_model=list[HighlightRead])
def list_highlights(
    book_id: int | None = None,
    page_number: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[HighlightRead]:
    query = select(Highlight).where(Highlight.user_id == current_user.id)
    if book_id is not None:
        query = query.where(Highlight.book_id == book_id)
    if page_number is not None:
        query = query.where(Highlight.page_number == page_number)
    rows = db.scalars(query.order_by(Highlight.created_at.desc(), Highlight.id.desc())).all()
    return [HighlightRead.model_validate(row) for row in rows]


@router.get("/{highlight_id}", response_model=HighlightRead)
def get_highlight(
    highlight_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HighlightRead:
    return HighlightRead.model_validate(owned_highlight(db, highlight_id, current_user.id))


@router.post("/", response_model=HighlightRead, status_code=status.HTTP_201_CREATED)
def create_highlight(
    payload: HighlightCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HighlightRead:
    validate_book(db, payload.book_id)
    validate_note(db, payload.note_id, current_user.id, payload.book_id)
    row = Highlight(user_id=current_user.id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return HighlightRead.model_validate(row)


@router.patch("/{highlight_id}", response_model=HighlightRead)
def update_highlight(
    highlight_id: int,
    payload: HighlightUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HighlightRead:
    row = owned_highlight(db, highlight_id, current_user.id)
    data = payload.model_dump(exclude_unset=True)
    validate_note(db, data.get("note_id", row.note_id), current_user.id, row.book_id)
    for field, value in data.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return HighlightRead.model_validate(row)


@router.delete("/{highlight_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_highlight(
    highlight_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    row = owned_highlight(db, highlight_id, current_user.id)
    db.delete(row)
    db.commit()
