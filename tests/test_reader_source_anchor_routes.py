from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401 - register all mapped tables
from app.core.database import Base
from app.models.archival_canvas import ArchivalCanvas
from app.models.archival_object import ArchivalObject
from app.models.book import Book
from app.models.user import User
from app.routes import bookmarks, highlights, notebook, quote_references, reader_source_anchors
from app.schemas.bookmark import BookmarkCreate, BookmarkUpdate
from app.schemas.highlight import HighlightCreate, HighlightUpdate
from app.schemas.note import NoteCreate, NoteUpdate
from app.schemas.quote_reference import QuoteReferenceCreate, QuoteReferenceUpdate
from app.services.reader_source_anchors import create_reader_source_anchor
from app.schemas.reader_source_anchor import ReaderSourceAnchorCreate


TABLE_NAMES = {
    "users",
    "collections",
    "archival_objects",
    "books",
    "book_assets",
    "archival_canvases",
    "archival_ocr_pages",
    "archival_rights",
    "reader_source_anchors",
    "bookmarks",
    "notebooks",
    "notes",
    "highlights",
    "quote_references",
}


def test_reader_records_can_attach_non_page_anchor_without_fabricating_page_number(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    tables = [table for table in Base.metadata.sorted_tables if table.name in TABLE_NAMES]
    Base.metadata.create_all(engine, tables=tables)

    monkeypatch.setattr(
        "app.services.reader_source_anchors.resolve_book_access",
        lambda _db, *, user_id, book_id: (True, "public", None),
    )
    monkeypatch.setattr(bookmarks, "get_effective_subscription", lambda *_args: None)
    monkeypatch.setattr(bookmarks, "get_effective_plan", lambda *_args: None)
    monkeypatch.setattr(notebook, "get_effective_subscription", lambda *_args: None)
    monkeypatch.setattr(notebook, "get_effective_plan", lambda *_args: None)
    monkeypatch.setattr(notebook, "notebook_limit_allows_note_creation", lambda *_args, **_kwargs: (True, 0, None))

    try:
        with Session(engine) as db:
            user = User(full_name="Reader", email="routes@example.test", password_hash="test")
            db.add(user)
            db.flush()
            book = Book(
                title="Archival source",
                author="Archive",
                cover="cover.jpg",
                description="Source record",
                source_type="pdf",
                visibility="published",
                pages=12,
            )
            db.add(book)
            db.flush()
            archival_object = ArchivalObject(
                identifier="AO-ROUTE-1",
                object_type="document",
                title=book.title,
                visibility="published",
            )
            db.add(archival_object)
            db.flush()
            book.archival_object_id = archival_object.id
            canvas = ArchivalCanvas(
                archival_object_id=archival_object.id,
                canvas_identifier="tl:canvas:route-test-1",
                sequence=1,
                label="Folio 1r",
                media_type="image/jpeg",
                width=100,
                height=150,
            )
            db.add(canvas)
            db.commit()

            payload = ReaderSourceAnchorCreate.model_validate(
                {
                    "book_id": book.id,
                    "locator": {"type": "iiif_canvas", "canvas_identifier": canvas.canvas_identifier},
                }
            )
            anchor = create_reader_source_anchor(db, user=user, book_id=book.id, locator=payload.locator)
            anchor_read = reader_source_anchors.get_source_anchor(anchor.id, db, user)
            assert anchor_read.source_is_current is True  # Canvas identity exists even without a versioned access image.

            bookmark = bookmarks.create_bookmark(
                BookmarkCreate(book_id=book.id, source_anchor_id=anchor.id), db, user
            )
            assert bookmark.source_anchor_id == anchor.id
            assert bookmark.page_number is None

            highlight = highlights.create_highlight(
                HighlightCreate(
                    book_id=book.id,
                    source_anchor_id=anchor.id,
                    selected_text="A passage on the canvas",
                ),
                db,
                user,
            )
            assert highlight.source_anchor_id == anchor.id
            assert highlight.page_number is None

            note = notebook.create_note(
                NoteCreate(
                    book_id=book.id,
                    source_anchor_id=anchor.id,
                    title="Canvas note",
                    body="A private note attached to a canvas.",
                ),
                db,
                user,
            )
            assert note.source_anchor_id == anchor.id
            assert note.page_number is None

            quote = quote_references.create_quote_reference(
                QuoteReferenceCreate(
                    book_id=book.id,
                    highlight_id=highlight.id,
                    note_id=note.id,
                    quote_text="A passage on the canvas",
                ),
                db,
                user,
            )
            assert quote.source_anchor_id == anchor.id
            assert quote.page_number is None

            updated_bookmark = bookmarks.update_bookmark(
                bookmark.id, BookmarkUpdate(note="Private canvas bookmark"), db, user
            )
            assert updated_bookmark.source_anchor_id == anchor.id
            assert updated_bookmark.page_number is None

            updated_highlight = highlights.update_highlight(
                highlight.id, HighlightUpdate(color="blue"), db, user
            )
            assert updated_highlight.source_anchor_id == anchor.id
            assert updated_highlight.page_number is None

            updated_note = notebook.update_note(
                note.id, NoteUpdate(body="Updated private research note."), db, user
            )
            assert updated_note.source_anchor_id == anchor.id
            assert updated_note.page_number is None

            updated_quote = quote_references.update_quote_reference(
                quote.id, QuoteReferenceUpdate(locator="canvas:tl:canvas:route-test-1"), db, user
            )
            assert updated_quote.source_anchor_id == anchor.id
            assert updated_quote.page_number is None
    finally:
        engine.dispose()
