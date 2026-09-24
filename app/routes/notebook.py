from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.book import Book
from app.models.bookmark import Bookmark
from app.models.note import Note
from app.models.notebook import Notebook
from app.models.user import User
from app.schemas.note import NoteCreate, NoteRead, NoteUpdate
from app.schemas.notebook import NotebookRead, NotebookUpdate

router = APIRouter(prefix="/notebook", tags=["notebook"])


def get_or_create_notebook(db: Session, user_id: int) -> Notebook:
    notebook = db.scalar(select(Notebook).where(Notebook.user_id == user_id))
    if notebook:
        return notebook
    notebook = Notebook(user_id=user_id, title="My Notebook")
    db.add(notebook)
    try:
        db.commit()
    except IntegrityError:
        # Another request may have created the user's singleton notebook between
        # the initial SELECT and INSERT. Roll back this session, then read the
        # authoritative row instead of surfacing a 500 to the client.
        db.rollback()
        notebook = db.scalar(select(Notebook).where(Notebook.user_id == user_id))
        if notebook is None:
            raise
        return notebook
    db.refresh(notebook)
    return notebook


def get_owned_note(db: Session, note_id: int, user_id: int) -> Note:
    note = db.scalar(
        select(Note)
        .join(Notebook)
        .where(Note.id == note_id, Notebook.user_id == user_id)
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


def validate_note_links(
    db: Session,
    user_id: int,
    book_id: int | None,
    bookmark_id: int | None,
) -> None:
    if bookmark_id is not None:
        bookmark = db.scalar(
            select(Bookmark).where(
                Bookmark.id == bookmark_id, Bookmark.user_id == user_id
            )
        )
        if not bookmark:
            raise HTTPException(status_code=404, detail="Bookmark not found")
        if book_id is not None and bookmark.book_id != book_id:
            raise HTTPException(
                status_code=400, detail="Bookmark does not belong to this book"
            )
        book_id = bookmark.book_id

    if book_id is not None:
        book = db.scalar(
            select(Book).where(Book.id == book_id, Book.archived_at.is_(None))
        )
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")


@router.get("", response_model=NotebookRead)
def get_notebook(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> NotebookRead:
    return NotebookRead.model_validate(get_or_create_notebook(db, current_user.id))


@router.patch("", response_model=NotebookRead)
def update_notebook(
    payload: NotebookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotebookRead:
    notebook = get_or_create_notebook(db, current_user.id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(notebook, field, value)
    db.commit()
    db.refresh(notebook)
    return NotebookRead.model_validate(notebook)


@router.get("/notes", response_model=list[NoteRead])
def list_notes(
    book_id: int | None = None,
    page_number: int | None = None,
    bookmark_id: int | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[NoteRead]:
    notebook = get_or_create_notebook(db, current_user.id)
    query = select(Note).where(Note.notebook_id == notebook.id)
    if book_id is not None:
        query = query.where(Note.book_id == book_id)
    if page_number is not None:
        query = query.where(Note.page_number == page_number)
    if bookmark_id is not None:
        query = query.where(Note.bookmark_id == bookmark_id)
    if q and q.strip():
        needle = f"%{q.strip()}%"
        query = query.where(Note.title.ilike(needle) | Note.body.ilike(needle))
    rows = db.scalars(query.order_by(Note.updated_at.desc(), Note.id.desc())).all()
    return [NoteRead.model_validate(row) for row in rows]


@router.post("/notes", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
def create_note(
    payload: NoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NoteRead:
    notebook = get_or_create_notebook(db, current_user.id)
    validate_note_links(db, current_user.id, payload.book_id, payload.bookmark_id)
    note = Note(
        notebook_id=notebook.id,
        book_id=payload.book_id,
        bookmark_id=payload.bookmark_id,
        page_number=payload.page_number,
        title=payload.title,
        body=payload.body,
    )
    if payload.bookmark_id is not None:
        bookmark = db.scalar(
            select(Bookmark).where(
                Bookmark.id == payload.bookmark_id, Bookmark.user_id == current_user.id
            )
        )
        if bookmark:
            note.book_id = bookmark.book_id
            note.page_number = note.page_number or bookmark.page_number
    db.add(note)
    db.commit()
    db.refresh(note)
    return NoteRead.model_validate(note)


@router.patch("/notes/{note_id}", response_model=NoteRead)
def update_note(
    note_id: int,
    payload: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NoteRead:
    note = get_owned_note(db, note_id, current_user.id)
    data = payload.model_dump(exclude_unset=True)
    next_book_id = data.get("book_id", note.book_id)
    next_bookmark_id = data.get("bookmark_id", note.bookmark_id)
    validate_note_links(db, current_user.id, next_book_id, next_bookmark_id)
    for field, value in data.items():
        setattr(note, field, value)
    if next_bookmark_id is not None:
        bookmark = db.scalar(
            select(Bookmark).where(
                Bookmark.id == next_bookmark_id, Bookmark.user_id == current_user.id
            )
        )
        if bookmark:
            note.book_id = bookmark.book_id
            note.page_number = note.page_number or bookmark.page_number
    db.commit()
    db.refresh(note)
    return NoteRead.model_validate(note)


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    note = get_owned_note(db, note_id, current_user.id)
    db.delete(note)
    db.commit()
