from __future__ import annotations

from datetime import datetime, timezone
import hashlib

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
import app.models  # noqa: F401 - register every mapped table before metadata use
from app.models.archival_canvas import ArchivalCanvas
from app.models.archival_object import ArchivalObject
from app.models.archival_ocr import ArchivalOCRPage
from app.models.book import Book
from app.models.book_asset import BookAsset
from app.models.collection import Collection
from app.models.reader_source_anchor import ReaderSourceAnchor
from app.models.user import User
from app.schemas.reader_source_anchor import ReaderSourceAnchorCreate
from app.services import reader_source_anchors as anchor_service
from app.services.reader_source_anchors import (
    create_reader_source_anchor,
    get_owned_source_anchor,
    is_source_anchor_current,
    resolve_legacy_page_number,
)


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
}


@pytest.fixture()
def db_session(monkeypatch: pytest.MonkeyPatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    tables = [table for table in Base.metadata.sorted_tables if table.name in TABLE_NAMES]
    Base.metadata.create_all(engine, tables=tables)
    monkeypatch.setattr(
        anchor_service,
        "resolve_book_access",
        lambda _db, *, user_id, book_id: (True, "public", None),
    )
    with Session(engine) as session:
        yield session
    engine.dispose()


def seed_user(db: Session) -> User:
    user = User(full_name="Reader", email="reader@example.test", password_hash="test")
    db.add(user)
    db.flush()
    return user


def seed_book(db: Session, *, source_type: str = "pdf", content_text: str | None = None) -> Book:
    book = Book(
        title="Archive source",
        author="Archive creator",
        cover="cover.jpg",
        description="Test source",
        source_type=source_type,
        content_text=content_text,
        visibility="published",
        pages=20,
        accession_no="ACC-TEST-0001",
    )
    db.add(book)
    db.flush()
    return book


def seed_archival_object(db: Session, book: Book) -> ArchivalObject:
    obj = ArchivalObject(
        identifier=f"AO-{book.id}",
        object_type="document",
        title=book.title,
        visibility="published",
    )
    db.add(obj)
    db.flush()
    book.archival_object_id = obj.id
    db.flush()
    return obj


def seed_asset(
    db: Session,
    user: User,
    book: Book,
    *,
    asset_type: str,
    mime_type: str,
    checksum: str = "a" * 64,
    version: int = 1,
    is_current: bool = True,
) -> BookAsset:
    asset = BookAsset(
        book_id=book.id,
        asset_type=asset_type,
        asset_role="access",
        version=version,
        original_filename=f"source-v{version}",
        storage_key=f"not-inspected/{book.id}/{version}",
        mime_type=mime_type,
        size_bytes=123,
        checksum_sha256=checksum,
        uploaded_by=user.id,
        is_current=is_current,
    )
    db.add(asset)
    db.flush()
    return asset


def test_pdf_page_anchor_snapshots_exact_asset_version(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    db = db_session
    user = seed_user(db)
    book = seed_book(db)
    asset = seed_asset(db, user, book, asset_type="pdf", mime_type="application/pdf", version=3, is_current=False)
    db.commit()

    payload = ReaderSourceAnchorCreate.model_validate(
        {"book_id": book.id, "locator": {"type": "pdf_page", "asset_id": asset.id, "page_number": 8}}
    )
    row = create_reader_source_anchor(db, user=user, book_id=payload.book_id, locator=payload.locator)

    assert row.locator_type == "pdf_page"
    assert row.locator_data["page_number"] == 8
    assert row.source_asset_id == asset.id
    assert row.source_asset_version == 3
    assert row.source_asset_checksum_sha256 == "a" * 64
    assert row.source_persistent_identifier is None
    assert row.source_accession_number == "ACC-TEST-0001"
    assert resolve_legacy_page_number(row, None) == 8


def test_pdf_text_locator_requires_page_local_non_empty_range(db_session: Session) -> None:
    with pytest.raises(ValueError):
        ReaderSourceAnchorCreate.model_validate(
            {"book_id": 1, "locator": {
                "type": "pdf_text", "asset_id": 2, "page_number": 1,
                "start_offset": 9, "end_offset": 9,
            }}
        )


def test_plain_text_span_snapshots_exact_transcription_checksum(db_session: Session) -> None:
    db = db_session
    user = seed_user(db)
    transcription = "First line\nSecond line — exact text."
    book = seed_book(db, source_type="text", content_text=transcription)
    db.commit()

    payload = ReaderSourceAnchorCreate.model_validate(
        {"book_id": book.id, "locator": {"type": "text_span", "start_offset": 0, "end_offset": 10}}
    )
    row = create_reader_source_anchor(db, user=user, book_id=book.id, locator=payload.locator)

    assert row.source_text_sha256 == hashlib.sha256(transcription.encode("utf-8")).hexdigest()
    assert row.source_asset_id is None


def test_plain_text_span_rejects_offsets_outside_source(db_session: Session) -> None:
    db = db_session
    user = seed_user(db)
    book = seed_book(db, source_type="text", content_text="short")
    db.commit()
    payload = ReaderSourceAnchorCreate.model_validate(
        {"book_id": book.id, "locator": {"type": "text_span", "start_offset": 0, "end_offset": 99}}
    )

    with pytest.raises(HTTPException) as exc:
        create_reader_source_anchor(db, user=user, book_id=book.id, locator=payload.locator)
    assert exc.value.status_code == 400


def test_iiif_canvas_anchor_uses_stable_canvas_identifier(db_session: Session) -> None:
    db = db_session
    user = seed_user(db)
    book = seed_book(db)
    obj = seed_archival_object(db, book)
    canvas = ArchivalCanvas(
        archival_object_id=obj.id,
        canvas_identifier="tl:canvas:stable-001",
        sequence=1,
        label="Folio 1r",
        media_type="image/jpeg",
        width=1200,
        height=1800,
    )
    db.add(canvas)
    db.commit()

    payload = ReaderSourceAnchorCreate.model_validate(
        {"book_id": book.id, "locator": {"type": "iiif_canvas", "canvas_identifier": canvas.canvas_identifier}}
    )
    row = create_reader_source_anchor(db, user=user, book_id=book.id, locator=payload.locator)

    assert row.archival_object_id == obj.id
    assert row.canvas_id == canvas.id
    assert row.source_persistent_identifier == obj.persistent_identifier
    assert row.source_accession_number == book.accession_no
    assert row.source_canvas_identifier == "tl:canvas:stable-001"


def test_image_region_must_fit_pixel_canvas(db_session: Session) -> None:
    db = db_session
    user = seed_user(db)
    book = seed_book(db)
    obj = seed_archival_object(db, book)
    asset = seed_asset(db, user, book, asset_type="image", mime_type="image/jpeg")
    canvas = ArchivalCanvas(
        archival_object_id=obj.id,
        asset_id=asset.id,
        canvas_identifier="tl:canvas:image-01",
        sequence=1,
        label="Recto",
        media_type="image/jpeg",
        width=1000,
        height=1500,
    )
    db.add(canvas)
    db.commit()
    payload = ReaderSourceAnchorCreate.model_validate(
        {"book_id": book.id, "locator": {
            "type": "image_region", "canvas_identifier": canvas.canvas_identifier,
            "x": 900, "y": 100, "width": 200, "height": 200, "coordinate_space": "pixel",
        }}
    )

    with pytest.raises(HTTPException) as exc:
        create_reader_source_anchor(db, user=user, book_id=book.id, locator=payload.locator)
    assert exc.value.status_code == 400
    assert "beyond" in str(exc.value.detail)


def test_ocr_span_requires_verified_matching_source(db_session: Session) -> None:
    db = db_session
    user = seed_user(db)
    book = seed_book(db)
    obj = seed_archival_object(db, book)
    checksum = "b" * 64
    asset = seed_asset(db, user, book, asset_type="image", mime_type="image/jpeg", checksum=checksum)
    canvas = ArchivalCanvas(
        archival_object_id=obj.id,
        asset_id=asset.id,
        canvas_identifier="tl:canvas:ocr-01",
        sequence=1,
        label="Folio",
        media_type="image/jpeg",
        width=1200,
        height=1800,
    )
    db.add(canvas)
    db.flush()
    text = "Verified transcription of this archival page."
    ocr = ArchivalOCRPage(
        archival_object_id=obj.id,
        canvas_id=canvas.id,
        source_asset_id=asset.id,
        source_checksum_sha256=checksum,
        text=text,
        language="eng",
        engine="tesseract",
        engine_version="5.4",
        status="verified",
        verified_at=datetime.now(timezone.utc),
    )
    db.add(ocr)
    db.commit()

    payload = ReaderSourceAnchorCreate.model_validate(
        {"book_id": book.id, "locator": {
            "type": "ocr_span", "canvas_identifier": canvas.canvas_identifier,
            "ocr_page_id": ocr.id, "start_offset": 0, "end_offset": 8,
        }}
    )
    row = create_reader_source_anchor(db, user=user, book_id=book.id, locator=payload.locator)
    assert row.ocr_page_id == ocr.id
    assert row.source_asset_checksum_sha256 == checksum
    assert row.source_text_sha256 == hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_ocr_span_rejects_stale_or_unverified_transcription(db_session: Session) -> None:
    db = db_session
    user = seed_user(db)
    book = seed_book(db)
    obj = seed_archival_object(db, book)
    checksum = "c" * 64
    asset = seed_asset(db, user, book, asset_type="image", mime_type="image/jpeg", checksum=checksum)
    canvas = ArchivalCanvas(
        archival_object_id=obj.id, asset_id=asset.id, canvas_identifier="tl:canvas:stale",
        sequence=1, label="Folio", media_type="image/jpeg", width=100, height=100,
    )
    db.add(canvas)
    db.flush()
    ocr = ArchivalOCRPage(
        archival_object_id=obj.id, canvas_id=canvas.id, source_asset_id=asset.id,
        source_checksum_sha256=checksum, text="unverified", language="eng",
        engine="tesseract", engine_version="5.4", status="stale", verified_at=None,
    )
    db.add(ocr)
    db.commit()
    payload = ReaderSourceAnchorCreate.model_validate(
        {"book_id": book.id, "locator": {
            "type": "ocr_span", "canvas_identifier": canvas.canvas_identifier,
            "ocr_page_id": ocr.id, "start_offset": 0, "end_offset": 3,
        }}
    )

    with pytest.raises(HTTPException) as exc:
        create_reader_source_anchor(db, user=user, book_id=book.id, locator=payload.locator)
    assert exc.value.status_code == 409


def test_media_time_range_is_bounded_by_canvas_duration(db_session: Session) -> None:
    db = db_session
    user = seed_user(db)
    book = seed_book(db)
    obj = seed_archival_object(db, book)
    asset = seed_asset(db, user, book, asset_type="video", mime_type="video/mp4")
    canvas = ArchivalCanvas(
        archival_object_id=obj.id, asset_id=asset.id, canvas_identifier="tl:canvas:video-01",
        sequence=1, label="Interview", media_type="video/mp4", duration_seconds=60.0,
    )
    db.add(canvas)
    db.commit()
    payload = ReaderSourceAnchorCreate.model_validate(
        {"book_id": book.id, "locator": {
            "type": "media_time", "canvas_identifier": canvas.canvas_identifier,
            "start_seconds": 10, "end_seconds": 75,
        }}
    )

    with pytest.raises(HTTPException) as exc:
        create_reader_source_anchor(db, user=user, book_id=book.id, locator=payload.locator)
    assert exc.value.status_code == 409

    valid_payload = ReaderSourceAnchorCreate.model_validate(
        {"book_id": book.id, "locator": {
            "type": "media_time", "canvas_identifier": canvas.canvas_identifier,
            "start_seconds": 10.5, "end_seconds": 30.0,
        }}
    )
    valid_anchor = create_reader_source_anchor(
        db, user=user, book_id=book.id, locator=valid_payload.locator
    )
    assert valid_anchor.locator_type == "media_time"
    assert valid_anchor.source_asset_id == asset.id
    assert valid_anchor.source_asset_version == asset.version


def test_source_anchor_is_user_owned_and_book_scoped(db_session: Session) -> None:
    db = db_session
    owner = seed_user(db)
    other = User(full_name="Other", email="other@example.test", password_hash="test")
    db.add(other)
    book = seed_book(db)
    asset = seed_asset(db, owner, book, asset_type="pdf", mime_type="application/pdf")
    db.commit()
    payload = ReaderSourceAnchorCreate.model_validate(
        {"book_id": book.id, "locator": {"type": "pdf_page", "asset_id": asset.id, "page_number": 1}}
    )
    row = create_reader_source_anchor(db, user=owner, book_id=book.id, locator=payload.locator)

    with pytest.raises(HTTPException) as exc:
        get_owned_source_anchor(db, source_anchor_id=row.id, user_id=other.id, book_id=book.id)
    assert exc.value.status_code == 404

    with pytest.raises(HTTPException) as exc:
        get_owned_source_anchor(db, source_anchor_id=row.id, user_id=owner.id, book_id=book.id + 1)
    assert exc.value.status_code == 400


def test_non_pdf_anchor_never_maps_to_legacy_page_number() -> None:
    anchor = ReaderSourceAnchor(
        id=1, user_id=1, book_id=1, locator_type="iiif_canvas",
        locator_data={"type": "iiif_canvas", "canvas_identifier": "tl:canvas:1"},
    )
    assert resolve_legacy_page_number(anchor, None) is None
    with pytest.raises(HTTPException):
        resolve_legacy_page_number(anchor, 1)


def test_locator_rejects_non_finite_coordinates_and_timestamps() -> None:
    with pytest.raises(ValueError):
        ReaderSourceAnchorCreate.model_validate(
            {"book_id": 1, "locator": {
                "type": "image_region", "canvas_identifier": "tl:canvas:1",
                "x": float("nan"), "y": 0, "width": 1, "height": 1,
            }}
        )
    with pytest.raises(ValueError):
        ReaderSourceAnchorCreate.model_validate(
            {"book_id": 1, "locator": {
                "type": "media_time", "canvas_identifier": "tl:canvas:audio",
                "start_seconds": 0, "end_seconds": float("inf"),
            }}
        )


def test_media_time_locator_requires_media_asset_not_only_canvas_label(db_session: Session) -> None:
    db = db_session
    user = seed_user(db)
    book = seed_book(db)
    obj = seed_archival_object(db, book)
    # A media label alone must not make an image file into a playable time source.
    image_asset = seed_asset(db, user, book, asset_type="image", mime_type="image/jpeg")
    canvas = ArchivalCanvas(
        archival_object_id=obj.id, asset_id=image_asset.id,
        canvas_identifier="tl:canvas:contradictory-media", sequence=1,
        label="Not actually audio", media_type="audio/mpeg", duration_seconds=45.0,
    )
    db.add(canvas)
    db.commit()
    payload = ReaderSourceAnchorCreate.model_validate(
        {"book_id": book.id, "locator": {
            "type": "media_time", "canvas_identifier": canvas.canvas_identifier,
            "start_seconds": 1, "end_seconds": 5,
        }}
    )

    with pytest.raises(HTTPException) as exc:
        create_reader_source_anchor(db, user=user, book_id=book.id, locator=payload.locator)
    assert exc.value.status_code == 409


def test_canvas_locators_reject_blank_identifiers() -> None:
    with pytest.raises(ValueError):
        ReaderSourceAnchorCreate.model_validate(
            {"book_id": 1, "locator": {"type": "iiif_canvas", "canvas_identifier": "   "}}
        )


def test_anchor_reports_stale_when_pdf_access_version_is_replaced(db_session: Session) -> None:
    db = db_session
    user = seed_user(db)
    book = seed_book(db)
    original = seed_asset(db, user, book, asset_type="pdf", mime_type="application/pdf", version=1)
    anchor = create_reader_source_anchor(
        db,
        user=user,
        book_id=book.id,
        locator=ReaderSourceAnchorCreate.model_validate({
            "book_id": book.id,
            "locator": {"type": "pdf_page", "asset_id": original.id, "page_number": 2},
        }).locator,
    )
    assert is_source_anchor_current(db, anchor) is True

    original.is_current = False
    db.flush()
    assert is_source_anchor_current(db, anchor) is False


def test_text_anchor_reports_stale_when_transcription_changes(db_session: Session) -> None:
    db = db_session
    user = seed_user(db)
    book = seed_book(db, source_type="text", content_text="Original transcription")
    anchor = create_reader_source_anchor(
        db,
        user=user,
        book_id=book.id,
        locator=ReaderSourceAnchorCreate.model_validate({
            "book_id": book.id,
            "locator": {"type": "text_span", "start_offset": 0, "end_offset": 8},
        }).locator,
    )
    assert is_source_anchor_current(db, anchor) is True
    book.content_text = "Revised transcription"
    db.flush()
    assert is_source_anchor_current(db, anchor) is False


def test_ocr_anchor_reports_stale_when_ocr_becomes_unverified(db_session: Session) -> None:
    db = db_session
    user = seed_user(db)
    book = seed_book(db)
    obj = seed_archival_object(db, book)
    checksum = "d" * 64
    asset = seed_asset(db, user, book, asset_type="image", mime_type="image/jpeg", checksum=checksum)
    canvas = ArchivalCanvas(
        archival_object_id=obj.id, asset_id=asset.id, canvas_identifier="tl:canvas:ocr-status",
        sequence=1, label="Folio", media_type="image/jpeg", width=120, height=180,
    )
    db.add(canvas)
    db.flush()
    ocr = ArchivalOCRPage(
        archival_object_id=obj.id, canvas_id=canvas.id, source_asset_id=asset.id,
        source_checksum_sha256=checksum, text="Verified text", language="eng",
        engine="tesseract", engine_version="5.4", status="verified",
        verified_at=datetime.now(timezone.utc),
    )
    db.add(ocr)
    db.flush()
    anchor = create_reader_source_anchor(
        db,
        user=user,
        book_id=book.id,
        locator=ReaderSourceAnchorCreate.model_validate({
            "book_id": book.id,
            "locator": {
                "type": "ocr_span", "canvas_identifier": canvas.canvas_identifier,
                "ocr_page_id": ocr.id, "start_offset": 0, "end_offset": 8,
            },
        }).locator,
    )
    assert is_source_anchor_current(db, anchor) is True
    ocr.status = "stale"
    db.flush()
    assert is_source_anchor_current(db, anchor) is False
