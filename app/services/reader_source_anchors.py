from __future__ import annotations

import hashlib
from typing import Any, NoReturn

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.archival_canvas import ArchivalCanvas
from app.models.archival_object import ArchivalObject
from app.models.archival_ocr import ArchivalOCRPage
from app.models.book import Book
from app.models.book_asset import BookAsset
from app.models.reader_source_anchor import ReaderSourceAnchor
from app.models.user import User
from app.schemas.reader_source_anchor import ReaderSourceLocator
from app.services.entitlements import resolve_book_access


def _not_found(detail: str) -> NoReturn:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _invalid(detail: str | dict[str, Any], code: int = status.HTTP_400_BAD_REQUEST) -> NoReturn:
    raise HTTPException(status_code=code, detail=detail)


def _get_published_archival_object(db: Session, book: Book) -> ArchivalObject:
    if book.archival_object_id is None:
        _invalid("This Book is not linked to an archival object", status.HTTP_409_CONFLICT)
    row = db.scalar(
        select(ArchivalObject)
        .options(selectinload(ArchivalObject.rights))
        .where(
            ArchivalObject.id == book.archival_object_id,
            ArchivalObject.archived_at.is_(None),
            ArchivalObject.visibility == "published",
        )
    )
    if row is None:
        _not_found("Published archival source not found")
    if row.rights is not None and row.rights.view_allowed is False:
        _invalid("Viewing this archival source is not permitted", status.HTTP_403_FORBIDDEN)
    return row


def _get_canvas(
    db: Session,
    archival_object: ArchivalObject,
    canvas_identifier: str,
) -> ArchivalCanvas:
    canvas = db.scalar(
        select(ArchivalCanvas)
        .options(selectinload(ArchivalCanvas.asset))
        .where(
            ArchivalCanvas.archival_object_id == archival_object.id,
            ArchivalCanvas.canvas_identifier == canvas_identifier,
        )
    )
    if canvas is None:
        _not_found("Canvas not found for this archival object")
    return canvas


def _get_pdf_asset(db: Session, book: Book, asset_id: int) -> BookAsset:
    asset = db.scalar(
        select(BookAsset).where(
            BookAsset.id == asset_id,
            BookAsset.book_id == book.id,
            BookAsset.asset_role == "access",
            BookAsset.asset_type == "pdf",
            BookAsset.mime_type == "application/pdf",
        )
    )
    if asset is None:
        _invalid("PDF locator must reference an access PDF asset belonging to this Book", status.HTTP_404_NOT_FOUND)
    return asset


def create_reader_source_anchor(
    db: Session,
    *,
    user: User,
    book_id: int,
    locator: ReaderSourceLocator,
) -> ReaderSourceAnchor:
    """Validate and persist an immutable source locator for private Reader use."""
    book = db.scalar(select(Book).where(Book.id == book_id, Book.archived_at.is_(None)))
    if book is None:
        _not_found("Book not found")

    allowed, reason, _ = resolve_book_access(db, user_id=user.id, book_id=book.id)
    if not allowed:
        _invalid(
            {"code": reason, "message": "Book access is required to create a source reference."},
            status.HTTP_403_FORBIDDEN,
        )

    archival_object: ArchivalObject | None = None
    canvas: ArchivalCanvas | None = None
    asset: BookAsset | None = None
    ocr_page: ArchivalOCRPage | None = None
    source_text_sha256: str | None = None

    kind = locator.type
    if kind in {"pdf_page", "pdf_text"}:
        asset = _get_pdf_asset(db, book, locator.asset_id)
        if book.pages > 0 and locator.page_number > book.pages:
            _invalid("PDF page number exceeds the catalogue page count")

    elif kind in {"iiif_canvas", "image_region", "ocr_span", "media_time"}:
        archival_object = _get_published_archival_object(db, book)
        canvas_identifier = locator.canvas_identifier
        canvas = _get_canvas(db, archival_object, canvas_identifier)
        # A canvas may be linked to a preservation master or a retired asset.
        # Only snapshot a current access representation that the public IIIF
        # surface can actually expose; never leak preservation-only asset IDs.
        linked_asset = canvas.asset
        expected_media_prefixes = ("audio/", "video/") if kind == "media_time" else ("image/",)
        asset = (
            linked_asset
            if linked_asset is not None
            and linked_asset.asset_role == "access"
            and linked_asset.is_current
            and linked_asset.mime_type.lower().startswith(expected_media_prefixes)
            else None
        )

        if kind == "image_region":
            if asset is None or not asset.mime_type.lower().startswith("image/"):
                _invalid("Image-region locators require a canvas linked to a current access image asset", status.HTTP_409_CONFLICT)
            if locator.coordinate_space == "pixel":
                if not canvas.width or not canvas.height:
                    _invalid("Pixel coordinates require recorded canvas width and height", status.HTTP_409_CONFLICT)
                if locator.x + locator.width > canvas.width or locator.y + locator.height > canvas.height:
                    _invalid("Image region extends beyond the canvas dimensions")

        elif kind == "ocr_span":
            ocr_page = db.scalar(
                select(ArchivalOCRPage).where(
                    ArchivalOCRPage.id == locator.ocr_page_id,
                    ArchivalOCRPage.archival_object_id == archival_object.id,
                    ArchivalOCRPage.canvas_id == canvas.id,
                    ArchivalOCRPage.status == "verified",
                    ArchivalOCRPage.verified_at.is_not(None),
                )
            )
            if ocr_page is None:
                _invalid("OCR locators require a verified OCR record for the selected canvas", status.HTTP_409_CONFLICT)
            source_asset = db.get(BookAsset, ocr_page.source_asset_id)
            if (
                source_asset is None
                or source_asset.asset_role != "access"
                or not source_asset.is_current
                or canvas.asset_id != source_asset.id
                or ocr_page.source_checksum_sha256.lower() != source_asset.checksum_sha256.lower()
            ):
                _invalid("OCR source asset or checksum no longer matches the archival canvas", status.HTTP_409_CONFLICT)
            if locator.end_offset > len(ocr_page.text):
                _invalid("OCR text range extends beyond the verified transcription")
            asset = source_asset
            source_text_sha256 = hashlib.sha256(ocr_page.text.encode("utf-8")).hexdigest()

        elif kind == "media_time":
            media_type = (canvas.media_type or "").lower()
            asset_mime_type = asset.mime_type.lower() if asset else ""
            if not (
                media_type.startswith(("audio/", "video/"))
                and asset_mime_type.startswith(("audio/", "video/"))
            ):
                _invalid(
                    "Media-time locators require a current access audio/video asset and matching canvas media type",
                    status.HTTP_409_CONFLICT,
                )
            if canvas.duration_seconds is None or locator.end_seconds > canvas.duration_seconds:
                _invalid("Media-time range exceeds the recorded canvas duration", status.HTTP_409_CONFLICT)

    elif kind == "text_span":
        if book.source_type.lower() != "text" or not book.content_text:
            _invalid("Text-span locators require a Book with an available plain-text representation", status.HTTP_409_CONFLICT)
        if locator.end_offset > len(book.content_text):
            _invalid("Text range extends beyond the Book transcription")
        source_text_sha256 = hashlib.sha256(book.content_text.encode("utf-8")).hexdigest()

    locator_data: dict[str, Any] = locator.model_dump(mode="json")
    row = ReaderSourceAnchor(
        user_id=user.id,
        book_id=book.id,
        archival_object_id=archival_object.id if archival_object else None,
        source_asset_id=asset.id if asset else None,
        canvas_id=canvas.id if canvas else None,
        ocr_page_id=ocr_page.id if ocr_page else None,
        locator_type=kind,
        locator_data=locator_data,
        source_persistent_identifier=(archival_object.persistent_identifier if archival_object else None),
        source_accession_number=book.accession_no,
        source_canvas_identifier=canvas.canvas_identifier if canvas else None,
        source_asset_version=asset.version if asset else None,
        source_asset_checksum_sha256=asset.checksum_sha256.lower() if asset else None,
        source_text_sha256=source_text_sha256,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_owned_source_anchor(
    db: Session,
    *,
    source_anchor_id: int | None,
    user_id: int,
    book_id: int | None = None,
) -> ReaderSourceAnchor | None:
    if source_anchor_id is None:
        return None
    row = db.scalar(
        select(ReaderSourceAnchor).where(
            ReaderSourceAnchor.id == source_anchor_id,
            ReaderSourceAnchor.user_id == user_id,
        )
    )
    if row is None:
        _not_found("Reader source anchor not found")
    if book_id is not None and row.book_id != book_id:
        _invalid("Reader source anchor belongs to a different Book")
    return row


def resolve_legacy_page_number(
    anchor: ReaderSourceAnchor | None,
    page_number: int | None,
) -> int | None:
    """Keep the legacy page column meaningful without mapping canvases to pages."""
    if anchor is None:
        return page_number
    if anchor.locator_type in {"pdf_page", "pdf_text"}:
        anchor_page = int(anchor.locator_data["page_number"])
        if page_number is not None and page_number != anchor_page:
            _invalid("Legacy page_number does not match the PDF source anchor")
        return anchor_page
    if page_number is not None:
        _invalid("Non-PDF source anchors must not be represented as Book page numbers")
    return None
