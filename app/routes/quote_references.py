from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.book import Book
from app.models.archival_canvas import ArchivalCanvas
from app.models.highlight import Highlight
from app.models.note import Note
from app.models.notebook import Notebook
from app.models.quote_reference import QuoteReference
from app.models.reader_source_anchor import ReaderSourceAnchor
from app.models.user import User
from app.schemas.quote_reference import QuoteReferenceCreate, QuoteReferenceRead, QuoteReferenceUpdate
from app.services.reader_source_anchors import get_owned_source_anchor, resolve_legacy_page_number

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


def validate_note(db: Session, note_id: int | None, user_id: int, book_id: int) -> Note | None:
    if note_id is None:
        return None
    note = db.scalar(select(Note).join(Notebook).where(Note.id == note_id, Notebook.user_id == user_id))
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.book_id is not None and note.book_id != book_id:
        raise HTTPException(status_code=400, detail="Note does not belong to this book")
    return note


def validate_highlight(db: Session, highlight_id: int | None, user_id: int, book_id: int) -> Highlight | None:
    if highlight_id is None:
        return None
    highlight = db.scalar(select(Highlight).where(Highlight.id == highlight_id, Highlight.user_id == user_id))
    if not highlight:
        raise HTTPException(status_code=404, detail="Highlight not found")
    if highlight.book_id != book_id:
        raise HTTPException(status_code=400, detail="Highlight does not belong to this book")
    return highlight


def _format_media_time(seconds: float) -> str:
    total = max(0.0, float(seconds))
    hours = int(total // 3600)
    minutes = int((total % 3600) // 60)
    remainder = total % 60
    if hours:
        return f"{hours}:{minutes:02d}:{remainder:05.2f}"
    return f"{minutes}:{remainder:05.2f}"


def format_source_anchor_location(
    anchor: ReaderSourceAnchor,
    *,
    canvas_label: str | None = None,
) -> str | None:
    """Build a human-readable citation locator without changing the anchor."""
    locator = anchor.locator_data or {}
    kind = anchor.locator_type
    if kind in {"pdf_page", "pdf_text"}:
        page = locator.get("page_number")
        if not isinstance(page, int) or page < 1:
            return None
        if kind == "pdf_text":
            start = locator.get("start_offset")
            end = locator.get("end_offset")
            if isinstance(start, int) and isinstance(end, int) and end > start:
                return f"p. {page}, text characters {start + 1}–{end}"
        return f"p. {page}"

    if kind == "text_span":
        start = locator.get("start_offset")
        end = locator.get("end_offset")
        if isinstance(start, int) and isinstance(end, int) and end > start:
            return f"text characters {start + 1}–{end}"
        return "plain-text transcription"

    canvas_identifier = anchor.source_canvas_identifier or locator.get("canvas_identifier")
    if kind in {"iiif_canvas", "image_region", "ocr_span", "media_time"}:
        canvas_name = f'Canvas “{canvas_label}”' if canvas_label else "Archival canvas"
        if canvas_identifier:
            canvas_name += f" [{canvas_identifier}]"
        if kind == "iiif_canvas":
            return canvas_name
        if kind == "image_region":
            coordinate_space = locator.get("coordinate_space", "pixel")
            x, y = locator.get("x"), locator.get("y")
            width, height = locator.get("width"), locator.get("height")
            if all(isinstance(value, (int, float)) for value in (x, y, width, height)):
                unit = "%" if coordinate_space == "percent" else "px"
                return f"{canvas_name}, region x={x:g}{unit}, y={y:g}{unit}, w={width:g}{unit}, h={height:g}{unit}"
            return f"{canvas_name}, image region"
        if kind == "ocr_span":
            start, end = locator.get("start_offset"), locator.get("end_offset")
            if isinstance(start, int) and isinstance(end, int) and end > start:
                return f"{canvas_name}, OCR characters {start + 1}–{end}"
            return f"{canvas_name}, OCR transcription"
        start, end = locator.get("start_seconds"), locator.get("end_seconds")
        if isinstance(start, (int, float)) and isinstance(end, (int, float)) and end > start:
            return f"{canvas_name}, { _format_media_time(start) }–{ _format_media_time(end) }"
        return canvas_name
    return None


def to_read(
    row: QuoteReference,
    book: Book,
    source_anchor: ReaderSourceAnchor | None = None,
    canvas_label: str | None = None,
) -> QuoteReferenceRead:
    citation = book.title
    location = format_source_anchor_location(source_anchor, canvas_label=canvas_label) if source_anchor else None
    if location:
        citation += f", {location}" if location.startswith("p. ") else f" — {location}"
    elif row.page_number is not None:
        citation += f", p. {row.page_number}"

    if source_anchor is not None:
        identifiers = []
        if source_anchor.source_accession_number:
            identifiers.append(f"Accession {source_anchor.source_accession_number}")
        if source_anchor.source_persistent_identifier:
            identifiers.append(f"Archival ID {source_anchor.source_persistent_identifier}")
        if identifiers:
            citation += f" — {'; '.join(identifiers)}"

    return QuoteReferenceRead(
        id=row.id,
        user_id=row.user_id,
        book_id=row.book_id,
        highlight_id=row.highlight_id,
        note_id=row.note_id,
        source_anchor_id=row.source_anchor_id,
        page_number=row.page_number,
        locator=row.locator,
        quote_text=row.quote_text,
        citation=f"{citation} — selected passage",
        source_title=book.title,
        source_author=book.author,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _citation_context(
    db: Session,
    row: QuoteReference,
    user_id: int,
) -> tuple[ReaderSourceAnchor | None, str | None]:
    anchor = get_owned_source_anchor(
        db,
        source_anchor_id=row.source_anchor_id,
        user_id=user_id,
        book_id=row.book_id,
    )
    canvas = db.get(ArchivalCanvas, anchor.canvas_id) if anchor and anchor.canvas_id else None
    return anchor, canvas.label if canvas else None


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
    anchor_ids = {row.source_anchor_id for row in rows if row.source_anchor_id is not None}
    anchors = {
        anchor.id: anchor
        for anchor in db.scalars(
            select(ReaderSourceAnchor).where(
                ReaderSourceAnchor.id.in_(anchor_ids or {-1}),
                ReaderSourceAnchor.user_id == current_user.id,
            )
        ).all()
    }
    canvas_ids = {anchor.canvas_id for anchor in anchors.values() if anchor.canvas_id is not None}
    canvas_labels = {
        canvas.id: canvas.label
        for canvas in db.scalars(select(ArchivalCanvas).where(ArchivalCanvas.id.in_(canvas_ids or {-1}))).all()
    }
    return [
        to_read(
            row,
            books[row.book_id],
            anchors.get(row.source_anchor_id),
            canvas_labels.get(anchors[row.source_anchor_id].canvas_id)
            if row.source_anchor_id in anchors and anchors[row.source_anchor_id].canvas_id is not None
            else None,
        )
        for row in rows
        if row.book_id in books
    ]


@router.get("/{reference_id}", response_model=QuoteReferenceRead)
def get_quote_reference(
    reference_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuoteReferenceRead:
    row = owned_reference(db, reference_id, current_user.id)
    anchor, canvas_label = _citation_context(db, row, current_user.id)
    return to_read(row, get_book(db, row.book_id), anchor, canvas_label)


@router.post("/", response_model=QuoteReferenceRead, status_code=status.HTTP_201_CREATED)
def create_quote_reference(
    payload: QuoteReferenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuoteReferenceRead:
    book = get_book(db, payload.book_id, active_only=True)
    highlight = validate_highlight(db, payload.highlight_id, current_user.id, payload.book_id)
    note = validate_note(db, payload.note_id, current_user.id, payload.book_id)

    anchor_id = payload.source_anchor_id
    if anchor_id is None:
        anchor_id = highlight.source_anchor_id if highlight else (note.source_anchor_id if note else None)
    anchor = get_owned_source_anchor(
        db, source_anchor_id=anchor_id, user_id=current_user.id, book_id=payload.book_id
    )
    requested_page = payload.page_number or (highlight.page_number if highlight else None)
    page_number = resolve_legacy_page_number(anchor, requested_page)
    locator = payload.locator or (highlight.position if highlight else None)
    quote_text = payload.quote_text
    row = QuoteReference(
        user_id=current_user.id,
        book_id=payload.book_id,
        highlight_id=payload.highlight_id,
        note_id=payload.note_id,
        source_anchor_id=anchor.id if anchor else None,
        page_number=page_number,
        locator=locator,
        quote_text=quote_text,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    anchor, canvas_label = _citation_context(db, row, current_user.id)
    return to_read(row, book, anchor, canvas_label)


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
        note = validate_note(db, data["note_id"], current_user.id, row.book_id)
        if "source_anchor_id" not in data and note is not None and note.source_anchor_id is not None:
            data["source_anchor_id"] = note.source_anchor_id
    if "source_anchor_id" in data:
        anchor = get_owned_source_anchor(
            db, source_anchor_id=data["source_anchor_id"], user_id=current_user.id, book_id=row.book_id
        )
        if anchor is not None:
            requested_page = data.get("page_number", row.page_number)
            if anchor.locator_type not in {"pdf_page", "pdf_text"} and "page_number" not in data:
                requested_page = None
            row.page_number = resolve_legacy_page_number(anchor, requested_page)
        else:
            row.source_anchor_id = None
    if "page_number" in data and "source_anchor_id" not in data and row.source_anchor_id is not None:
        anchor = get_owned_source_anchor(
            db, source_anchor_id=row.source_anchor_id, user_id=current_user.id, book_id=row.book_id
        )
        row.page_number = resolve_legacy_page_number(anchor, data["page_number"])
    for field, value in data.items():
        if field not in {"source_anchor_id", "page_number"}:
            setattr(row, field, value)
    if "source_anchor_id" in data and data["source_anchor_id"] is not None:
        row.source_anchor_id = data["source_anchor_id"]
    elif "source_anchor_id" in data:
        row.source_anchor_id = None
    if "page_number" in data and row.source_anchor_id is None:
        row.page_number = data["page_number"]
    db.commit()
    db.refresh(row)
    anchor, canvas_label = _citation_context(db, row, current_user.id)
    return to_read(row, get_book(db, row.book_id), anchor, canvas_label)


@router.delete("/{reference_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quote_reference(
    reference_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    row = owned_reference(db, reference_id, current_user.id)
    db.delete(row)
    db.commit()
