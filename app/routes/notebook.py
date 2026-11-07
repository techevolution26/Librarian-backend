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
from app.models.reader_source_anchor import ReaderSourceAnchor
from app.models.user import User
from app.schemas.note import NoteCreate, NoteRead, NoteUpdate
from app.schemas.notebook import NotebookRead, NotebookUpdate
from app.services.notebook_limits import get_notebook_note_count, notebook_limit_allows_note_creation
from app.services.reader_source_anchors import get_owned_source_anchor, resolve_legacy_page_number
from app.services.subscription_billing import get_effective_plan, get_effective_subscription

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
        select(Note).join(Notebook).where(Note.id == note_id, Notebook.user_id == user_id)
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


def validate_note_links(
    db: Session,
    user_id: int,
    book_id: int | None,
    bookmark_id: int | None,
    source_anchor_id: int | None = None,
    *,
    inherit_bookmark_anchor: bool = True,
) -> tuple[int | None, int | None, Bookmark | None, ReaderSourceAnchor | None]:
    bookmark = None
    if bookmark_id is not None:
        bookmark = db.scalar(
            select(Bookmark).where(Bookmark.id == bookmark_id, Bookmark.user_id == user_id)
        )
        if not bookmark:
            raise HTTPException(status_code=404, detail="Bookmark not found")
        if book_id is not None and bookmark.book_id != book_id:
            raise HTTPException(status_code=400, detail="Bookmark does not belong to this book")
        book_id = bookmark.book_id
        if source_anchor_id is None and inherit_bookmark_anchor:
            source_anchor_id = bookmark.source_anchor_id

    anchor = get_owned_source_anchor(
        db, source_anchor_id=source_anchor_id, user_id=user_id, book_id=book_id
    )
    if anchor is not None:
        if book_id is not None and anchor.book_id != book_id:
            raise HTTPException(status_code=400, detail="Source anchor does not belong to this book")
        book_id = anchor.book_id

    if book_id is not None:
        book = db.scalar(select(Book).where(Book.id == book_id, Book.archived_at.is_(None)))
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

    return book_id, (anchor.id if anchor else None), bookmark, anchor


@router.get("", response_model=NotebookRead)
def get_notebook(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> NotebookRead:
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


@router.get("/usage")
def notebook_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    """Return current private notebook-note usage without assuming a plan."""
    return {"note_count": get_notebook_note_count(db, user_id=current_user.id)}


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
    # Serialize per-user creation against concurrent requests so a finite
    # notebook-note ceiling cannot be exceeded by two simultaneous inserts.
    db.execute(select(User).where(User.id == current_user.id).with_for_update())

    notebook = db.scalar(select(Notebook).where(Notebook.user_id == current_user.id))
    if notebook is None:
        notebook = Notebook(user_id=current_user.id, title="My Notebook")
        db.add(notebook)
        db.flush()

    book_id, source_anchor_id, bookmark, source_anchor = validate_note_links(
        db,
        current_user.id,
        payload.book_id,
        payload.bookmark_id,
        payload.source_anchor_id,
    )
    page_number = resolve_legacy_page_number(source_anchor, payload.page_number)
    if source_anchor is None and bookmark is not None and page_number is None:
        page_number = bookmark.page_number

    effective_subscription = get_effective_subscription(db, current_user.id)
    effective_plan = None if effective_subscription is not None else get_effective_plan(db, current_user.id)
    effective_plan_id = effective_subscription.plan_id if effective_subscription is not None else (effective_plan.id if effective_plan else None)
    if effective_plan_id is not None:
        allowed, current_count, limit = notebook_limit_allows_note_creation(
            db,
            user_id=current_user.id,
            plan_id=effective_plan_id,
        )
        if not allowed:
            detail = (
                "Notebook note limit reached"
                if limit is not None
                else "Notebook notes are not enabled for your current plan"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "notebook_note_limit_reached",
                    "message": detail,
                    "count": current_count,
                    "limit": limit,
                },
            )
    note = Note(
        notebook_id=notebook.id,
        book_id=book_id,
        bookmark_id=payload.bookmark_id,
        page_number=page_number,
        source_anchor_id=source_anchor_id,
        title=payload.title,
        body=payload.body,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return NoteRead.model_validate(note)


@router.get("/notes/{note_id}", response_model=NoteRead)
def get_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NoteRead:
    return NoteRead.model_validate(get_owned_note(db, note_id, current_user.id))


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
    if "source_anchor_id" in data:
        next_anchor_id = data["source_anchor_id"]
        inherit_bookmark_anchor = False
    elif "bookmark_id" in data and next_bookmark_id != note.bookmark_id:
        next_anchor_id = None
        inherit_bookmark_anchor = True
    else:
        next_anchor_id = note.source_anchor_id
        inherit_bookmark_anchor = False

    resolved_book_id, resolved_anchor_id, bookmark, anchor = validate_note_links(
        db,
        current_user.id,
        next_book_id,
        next_bookmark_id,
        next_anchor_id,
        inherit_bookmark_anchor=inherit_bookmark_anchor,
    )
    requested_page = data.get("page_number", note.page_number)
    if anchor is not None and anchor.id != note.source_anchor_id and anchor.locator_type not in {"pdf_page", "pdf_text"} and "page_number" not in data:
        requested_page = None
    resolved_page = resolve_legacy_page_number(anchor, requested_page)
    if anchor is None and bookmark is not None and "page_number" not in data and "bookmark_id" in data:
        resolved_page = bookmark.page_number

    note.book_id = resolved_book_id
    note.bookmark_id = next_bookmark_id
    note.source_anchor_id = resolved_anchor_id
    note.page_number = resolved_page
    for field, value in data.items():
        if field not in {"book_id", "bookmark_id", "source_anchor_id", "page_number"}:
            setattr(note, field, value)
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
