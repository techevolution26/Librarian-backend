from __future__ import annotations

from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - register all mapped tables
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models.archival_canvas import ArchivalCanvas
from app.models.archival_object import ArchivalObject
from app.models.book import Book
from app.models.user import User
from app.routes import bookmarks as bookmarks_route
from app.routes import notebook as notebook_route
from app.services import reader_source_anchors as anchor_service


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


def test_source_anchor_http_flow_preserves_canvas_identity_and_legacy_pages(monkeypatch):
    """Exercise the same HTTP routes consumed by the Expo Reader client."""
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [table for table in Base.metadata.sorted_tables if table.name in TABLE_NAMES]
    Base.metadata.create_all(engine, tables=tables)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with session_factory() as db:
        user = User(full_name="Reader API", email="reader-api@example.test", password_hash="test")
        other_user = User(full_name="Other Reader", email="other-reader-api@example.test", password_hash="test")
        db.add_all([user, other_user])
        db.flush()
        book = Book(
            title="Runtime archive",
            author="Archive",
            cover="cover.jpg",
            description="HTTP integration source",
            source_type="pdf",
            visibility="published",
            pages=8,
            accession_no="ACC-RUNTIME-1",
        )
        db.add(book)
        db.flush()
        archival_object = ArchivalObject(
            identifier="AO-RUNTIME-1",
            object_type="document",
            title=book.title,
            visibility="published",
        )
        db.add(archival_object)
        db.flush()
        book.archival_object_id = archival_object.id
        canvas = ArchivalCanvas(
            archival_object_id=archival_object.id,
            canvas_identifier="tl:canvas:runtime-1",
            sequence=1,
            label="Folio 1r",
            media_type="image/jpeg",
            width=1200,
            height=1800,
        )
        db.add(canvas)
        db.commit()
        user_id = user.id
        other_user_id = other_user.id
        book_id = book.id

    monkeypatch.setattr(
        anchor_service,
        "resolve_book_access",
        lambda _db, *, user_id, book_id: (True, "public", None),
    )
    for route in (bookmarks_route, notebook_route):
        monkeypatch.setattr(route, "get_effective_subscription", lambda *_args: None)
        monkeypatch.setattr(route, "get_effective_plan", lambda *_args: None)
    monkeypatch.setattr(
        notebook_route,
        "notebook_limit_allows_note_creation",
        lambda *_args, **_kwargs: (True, 0, None),
    )

    active_user_id = {"value": user_id}

    def override_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    def override_user() -> User:
        with session_factory() as db:
            row = db.get(User, active_user_id["value"])
            assert row is not None
            return row

    monkeypatch.setitem(app.dependency_overrides, get_db, override_db)
    monkeypatch.setitem(app.dependency_overrides, get_current_user, override_user)

    try:
        with TestClient(app) as client:
            created = client.post(
                "/reader/source-anchors",
                json={
                    "book_id": book_id,
                    "locator": {
                        "type": "iiif_canvas",
                        "canvas_identifier": "tl:canvas:runtime-1",
                    },
                },
            )
            assert created.status_code == 201, created.text
            anchor = created.json()
            anchor_id = anchor["id"]
            assert anchor["source_is_current"] is True
            assert anchor["locator"]["type"] == "iiif_canvas"

            fetched = client.get(f"/reader/source-anchors/{anchor_id}")
            assert fetched.status_code == 200
            assert fetched.json()["id"] == anchor_id
            listed = client.get("/reader/source-anchors", params={"book_id": book_id})
            assert listed.status_code == 200
            assert any(row["id"] == anchor_id for row in listed.json())

            bookmark = client.post(
                "/bookmarks/",
                json={"book_id": book_id, "source_anchor_id": anchor_id, "title": "Folio bookmark"},
            )
            assert bookmark.status_code == 201, bookmark.text
            assert bookmark.json()["source_anchor_id"] == anchor_id
            assert bookmark.json()["page_number"] is None

            highlight = client.post(
                "/highlights/",
                json={
                    "book_id": book_id,
                    "source_anchor_id": anchor_id,
                    "selected_text": "A passage on folio 1r",
                },
            )
            assert highlight.status_code == 201, highlight.text
            assert highlight.json()["source_anchor_id"] == anchor_id
            assert highlight.json()["page_number"] is None

            note = client.post(
                "/notebook/notes",
                json={
                    "book_id": book_id,
                    "source_anchor_id": anchor_id,
                    "title": "Folio note",
                    "body": "Private archival research.",
                },
            )
            assert note.status_code == 201, note.text
            assert note.json()["source_anchor_id"] == anchor_id
            assert note.json()["page_number"] is None

            developed = client.post(f"/highlights/{highlight.json()['id']}/develop")
            assert developed.status_code == 200, developed.text
            assert developed.json()["source_anchor_id"] == anchor_id
            assert developed.json()["page_number"] is None

            quote = client.post(
                "/quote-references/",
                json={
                    "book_id": book_id,
                    "highlight_id": highlight.json()["id"],
                    "note_id": developed.json()["id"],
                    "quote_text": "A passage on folio 1r",
                },
            )
            assert quote.status_code == 201, quote.text
            assert quote.json()["source_anchor_id"] == anchor_id
            assert "Folio 1r" in quote.json()["citation"]
            assert "ACC-RUNTIME-1" in quote.json()["citation"]

            # Existing page-based clients must continue to create real pages.
            legacy_bookmark = client.post(
                "/bookmarks/",
                json={"book_id": book_id, "page_number": 4, "title": "Legacy page"},
            )
            assert legacy_bookmark.status_code == 201, legacy_bookmark.text
            assert legacy_bookmark.json()["page_number"] == 4
            assert legacy_bookmark.json()["source_anchor_id"] is None

            legacy_highlight = client.post(
                "/highlights/",
                json={"book_id": book_id, "page_number": 4, "selected_text": "Legacy passage"},
            )
            assert legacy_highlight.status_code == 201, legacy_highlight.text
            assert legacy_highlight.json()["page_number"] == 4
            assert legacy_highlight.json()["source_anchor_id"] is None

            # Anchors are private to their creating user.
            active_user_id["value"] = other_user_id
            forbidden_lookup = client.get(f"/reader/source-anchors/{anchor_id}")
            assert forbidden_lookup.status_code == 404
    finally:
        engine.dispose()
