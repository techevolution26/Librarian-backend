from __future__ import annotations

from collections.abc import Generator
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models.archival_canvas import ArchivalCanvas
from app.models.archival_object import ArchivalObject
from app.models.archival_rights import ArchivalRights
from app.models.book import Book
from app.models.book_asset import BookAsset
from app.models.preservation_event import PreservationEvent
from app.models.user import User
from app.routes import books as books_route


def _png_bytes(color: tuple[int, int, int]) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (48, 64), color).save(buffer, format="PNG")
    return buffer.getvalue()


def _client(monkeypatch, tmp_path: Path):
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    @event.listens_for(engine, "connect")
    def _register_sqlite_functions(connection, _record):
        connection.create_function("char_length", 1, len)

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as db:
        admin = User(
            full_name="Archive Admin",
            email="archive-admin@example.test",
            password_hash="test-only",
            role="ADMIN",
        )
        db.add(admin)
        db.commit()
        admin_id = admin.id

    storage = tmp_path / "test-storage"
    books_dir = storage / "books"
    covers_dir = storage / "covers"
    monkeypatch.setattr(books_route, "BOOKS_STORAGE_DIR", books_dir)
    monkeypatch.setattr(books_route, "COVERS_STORAGE_DIR", covers_dir)
    monkeypatch.setattr(
        books_route,
        "get_settings",
        lambda: SimpleNamespace(
            max_pdf_upload_mb=10,
            max_text_upload_mb=10,
            max_archival_image_upload_mb=10,
            max_archival_canvas_count=20,
            max_archival_ingest_total_mb=100,
            max_cover_upload_mb=10,
        ),
    )

    def override_db() -> Generator[Session, None, None]:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    def override_user() -> User:
        with factory() as db:
            row = db.get(User, admin_id)
            assert row is not None
            return row

    monkeypatch.setitem(app.dependency_overrides, get_db, override_db)
    monkeypatch.setitem(app.dependency_overrides, get_current_user, override_user)
    return TestClient(app), factory, engine


def test_admin_ingest_text_with_multiple_iiif_canvases_and_rights_lifecycle(monkeypatch, tmp_path):
    client, factory, engine = _client(monkeypatch, tmp_path)
    try:
        files = [
            ("text_file", ("transcription.txt", "Transcribed archival text\nwith a second line.".encode(), "text/plain")),
            ("canvas_files", ("folio-1.png", _png_bytes((160, 40, 40)), "image/png")),
            ("canvas_files", ("folio-2.png", _png_bytes((40, 90, 160)), "image/png")),
        ]
        response = client.post(
            "/books/ingest",
            data={
                "material_type": "text",
                "title": "Field Notebook",
                "author": "A. Researcher",
                "description": "A transcript with its digitised folios.",
                "rights_decision": "pending",
                "rights_statement": "all-rights-reserved",
                "archival_object_type": "manuscript",
                "source_institution": "Regional Archive",
                "source_collection": "Field Records",
                "shelfmark": "FR-12/4",
                "digitization_method": "Overhead capture",
            },
            files=files,
        )
        assert response.status_code == 201, response.text
        created = response.json()
        assert created["source_type"] == "text"
        assert created["archival_object_id"] is not None
        book_id = created["id"]
        object_id = created["archival_object_id"]

        with factory() as db:
            book = db.get(Book, book_id)
            assert book is not None
            assert book.content_text.startswith("Transcribed archival text")
            assert book.archival_object is not None
            assert book.archival_object.rights is not None
            assert book.archival_object.rights.view_allowed is None
            canvases = db.scalars(
                select(ArchivalCanvas).where(ArchivalCanvas.archival_object_id == object_id).order_by(ArchivalCanvas.sequence)
            ).all()
            assert [canvas.sequence for canvas in canvases] == [1, 2]
            assert [canvas.label for canvas in canvases] == ["folio-1", "folio-2"]
            assets = db.scalars(select(BookAsset).where(BookAsset.book_id == book_id, BookAsset.asset_type == "image")).all()
            assert len(assets) == 2
            assert len({asset.logical_key for asset in assets}) == 2
            assert all(asset.is_current for asset in assets)
            assert db.scalar(select(PreservationEvent.id).where(PreservationEvent.archival_object_id == object_id)) is not None
            first_canvas_id = canvases[0].id
            first_identifier = canvases[0].canvas_identifier

        # A fresh decision permits a draft record to be published.
        reviewed = client.post(
            f"/archival-objects/admin/{object_id}/rights-review",
            json={"decision": "allow", "rights_holder": "Regional Archive", "rights_source": "Signed agreement"},
        )
        assert reviewed.status_code == 200, reviewed.text
        published = client.patch(f"/books/{book_id}/publish")
        assert published.status_code == 200, published.text
        assert published.json()["visibility"] == "published"
        manifest = client.get(f"/archival-objects/{object_id}/iiif/manifest")
        assert manifest.status_code == 200, manifest.text
        assert len(manifest.json()["items"]) == 2

        # Adding a canvas withdraws the published object and clears the old review.
        added = client.post(
            f"/books/{book_id}/canvases",
            files=[("image_files", ("folio-3.png", _png_bytes((40, 140, 70)), "image/png"))],
        )
        assert added.status_code == 201, added.text
        assert added.json()["visibility"] == "draft"
        hidden_manifest = client.get(f"/archival-objects/{object_id}/iiif/manifest")
        assert hidden_manifest.status_code == 404
        with factory() as db:
            obj = db.get(ArchivalObject, object_id)
            book = db.get(Book, book_id)
            assert obj is not None and book is not None
            assert obj.visibility == "draft"
            assert obj.rights is not None and obj.rights.view_allowed is None
            assert obj.rights.verified_at is None
            assert book.visibility == "draft"
            assert db.scalar(select(ArchivalCanvas.id).where(ArchivalCanvas.archival_object_id == object_id, ArchivalCanvas.sequence == 3)) is not None

        # Replacing a canvas keeps the stable canvas identifier and versions its asset.
        reviewed_again = client.post(
            f"/archival-objects/admin/{object_id}/rights-review",
            json={"decision": "allow", "rights_holder": "Regional Archive", "rights_source": "Updated source check"},
        )
        assert reviewed_again.status_code == 200, reviewed_again.text
        republished = client.patch(f"/books/{book_id}/publish")
        assert republished.status_code == 200, republished.text
        replaced = client.patch(
            f"/books/{book_id}/canvases/{first_canvas_id}/image",
            files={"image_file": ("folio-1-revised.png", _png_bytes((10, 10, 10)), "image/png")},
        )
        assert replaced.status_code == 200, replaced.text
        with factory() as db:
            canvas = db.get(ArchivalCanvas, first_canvas_id)
            assert canvas is not None
            assert canvas.canvas_identifier == first_identifier
            versions = db.scalars(
                select(BookAsset).where(BookAsset.book_id == book_id, BookAsset.asset_type == "image", BookAsset.logical_key == first_identifier).order_by(BookAsset.version)
            ).all()
            assert [asset.version for asset in versions] == [1, 2]
            assert [asset.is_current for asset in versions] == [False, True]
            obj = db.get(ArchivalObject, object_id)
            assert obj is not None and obj.rights is not None
            assert obj.rights.view_allowed is None and obj.visibility == "draft"
    finally:
        client.close()
        app.dependency_overrides.clear()
        engine.dispose()


def test_admin_ingest_rejects_invalid_utf8_without_creating_record(monkeypatch, tmp_path):
    client, factory, engine = _client(monkeypatch, tmp_path)
    try:
        response = client.post(
            "/books/ingest",
            data={"material_type": "text", "title": "Bad text", "author": "Unknown", "description": "Invalid encoding"},
            files={"text_file": ("bad.txt", b"\xff\xfe\x00", "text/plain")},
        )
        assert response.status_code == 400, response.text
        with factory() as db:
            assert db.scalar(select(Book.id).where(Book.title == "Bad text")) is None
    finally:
        client.close()
        app.dependency_overrides.clear()
        engine.dispose()


def test_admin_ingest_facsimile_requires_image_sources(monkeypatch, tmp_path):
    client, _factory, engine = _client(monkeypatch, tmp_path)
    try:
        response = client.post(
            "/books/ingest",
            data={"material_type": "facsimile", "title": "No scans", "author": "Unknown", "description": "Missing images"},
        )
        assert response.status_code == 400
        assert "requires one or more archival images" in response.text
    finally:
        client.close()
        app.dependency_overrides.clear()
        engine.dispose()


def test_admin_ingest_pdf_with_supplementary_scanned_canvases(monkeypatch, tmp_path):
    client, factory, engine = _client(monkeypatch, tmp_path)
    try:
        response = client.post(
            "/books/ingest",
            data={
                "material_type": "pdf",
                "title": "Digitised Register",
                "author": "County Records Office",
                "description": "A born-digital access copy with supplementary scan images.",
                "rights_decision": "pending",
                "archival_object_type": "document",
            },
            files=[
                ("pdf_file", ("register.pdf", b"%PDF-1.7\n% test fixture\n", "application/pdf")),
                ("canvas_files", ("cover-folio.png", _png_bytes((120, 120, 40)), "image/png")),
                ("canvas_files", ("signature-folio.png", _png_bytes((40, 120, 120)), "image/png")),
            ],
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["source_type"] == "pdf"
        book_id = body["id"]
        with factory() as db:
            book = db.get(Book, book_id)
            assert book is not None and book.source_path
            assert len([asset for asset in book.assets if asset.asset_type == "pdf" and asset.is_current]) == 1
            images = [asset for asset in book.assets if asset.asset_type == "image" and asset.is_current]
            assert len(images) == 2
            canvases = db.scalars(
                select(ArchivalCanvas).where(ArchivalCanvas.archival_object_id == book.archival_object_id)
            ).all()
            assert len(canvases) == 2
    finally:
        client.close()
        app.dependency_overrides.clear()
        engine.dispose()


def test_canvas_replacement_respects_aggregate_limit_and_preserves_current_asset(monkeypatch, tmp_path):
    client, factory, engine = _client(monkeypatch, tmp_path)
    try:
        created = client.post(
            "/books/ingest",
            data={
                "material_type": "facsimile", "title": "Small Scan Set", "author": "Archive",
                "description": "One small current canvas.", "rights_decision": "pending",
            },
            files=[("canvas_files", ("folio.png", _png_bytes((200, 20, 20)), "image/png"))],
        )
        assert created.status_code == 201, created.text
        book_id = created.json()["id"]
        with factory() as db:
            book = db.get(Book, book_id)
            assert book is not None and book.archival_object is not None
            canvas = db.scalar(select(ArchivalCanvas).where(ArchivalCanvas.archival_object_id == book.archival_object.id))
            assert canvas is not None
            canvas_id = canvas.id
            original_asset_id = canvas.asset_id

        monkeypatch.setattr(books_route, "get_settings", lambda: SimpleNamespace(
            max_pdf_upload_mb=10, max_text_upload_mb=10, max_archival_image_upload_mb=10,
            max_archival_canvas_count=20, max_archival_ingest_total_mb=0, max_cover_upload_mb=10,
        ))
        rejected = client.patch(
            f"/books/{book_id}/canvases/{canvas_id}/image",
            files={"image_file": ("replacement.png", _png_bytes((20, 20, 200)), "image/png")},
        )
        assert rejected.status_code == 413, rejected.text
        with factory() as db:
            canvas = db.get(ArchivalCanvas, canvas_id)
            assert canvas is not None and canvas.asset_id == original_asset_id
            original = db.get(BookAsset, original_asset_id)
            assert original is not None and original.is_current is True
            assert len(db.scalars(select(BookAsset).where(BookAsset.book_id == book_id, BookAsset.asset_type == "image")).all()) == 1
    finally:
        client.close()
        app.dependency_overrides.clear()
        engine.dispose()


def test_appending_canvases_counts_new_assets_once_and_uses_decoded_image_format(monkeypatch, tmp_path):
    client, factory, engine = _client(monkeypatch, tmp_path)
    try:
        created = client.post(
            "/books/ingest",
            data={
                "material_type": "facsimile", "title": "Canvas Sequence", "author": "Archive",
                "description": "A source set for an aggregate-limit regression test.", "rights_decision": "pending",
            },
            files=[("canvas_files", ("first.png", _png_bytes((30, 30, 30)), "image/png"))],
        )
        assert created.status_code == 201, created.text
        book_id = created.json()["id"]
        with factory() as db:
            book = db.get(Book, book_id)
            assert book is not None
            existing_size = int(db.scalar(select(func.coalesce(func.sum(BookAsset.size_bytes), 0)).where(
                BookAsset.book_id == book_id, BookAsset.asset_role == "access", BookAsset.is_current.is_(True),
            )) or 0)

        second_image = _png_bytes((220, 220, 220))
        allowed_total = existing_size + len(second_image) + 1
        monkeypatch.setattr(books_route, "get_settings", lambda: SimpleNamespace(
            max_pdf_upload_mb=10, max_text_upload_mb=10, max_archival_image_upload_mb=10,
            max_archival_canvas_count=20, max_archival_ingest_total_mb=allowed_total / (1024 * 1024),
            max_cover_upload_mb=10,
        ))
        added = client.post(
            f"/books/{book_id}/canvases",
            files=[("image_files", ("second.jpg", second_image, "image/png"))],
        )
        assert added.status_code == 201, added.text
        with factory() as db:
            book = db.get(Book, book_id)
            assert book is not None and book.archival_object is not None
            canvases = db.scalars(select(ArchivalCanvas).where(ArchivalCanvas.archival_object_id == book.archival_object.id)).all()
            assert len(canvases) == 2
            second = next(asset for asset in book.assets if asset.original_filename == "second.jpg")
            assert second.mime_type == "image/png"
    finally:
        client.close()
        app.dependency_overrides.clear()
        engine.dispose()


def test_deleting_canvas_retires_access_asset_and_records_preservation_event(monkeypatch, tmp_path):
    client, factory, engine = _client(monkeypatch, tmp_path)
    try:
        created = client.post(
            "/books/ingest",
            data={
                "material_type": "facsimile", "title": "Withdrawn Scan", "author": "Archive",
                "description": "A canvas to be removed from the current presentation.", "rights_decision": "pending",
            },
            files=[("canvas_files", ("folio.png", _png_bytes((150, 60, 20)), "image/png"))],
        )
        assert created.status_code == 201, created.text
        book_id = created.json()["id"]
        object_id = created.json()["archival_object_id"]
        with factory() as db:
            book = db.get(Book, book_id)
            assert book is not None and book.archival_object is not None
            canvas = db.scalar(select(ArchivalCanvas).where(ArchivalCanvas.archival_object_id == object_id))
            assert canvas is not None and canvas.asset_id is not None
            canvas_id, asset_id = canvas.id, canvas.asset_id

        reviewed = client.post(
            f"/archival-objects/admin/{object_id}/rights-review",
            json={"decision": "allow", "rights_source": "Repository permission letter"},
        )
        assert reviewed.status_code == 200, reviewed.text
        published = client.patch(f"/books/{book_id}/publish")
        assert published.status_code == 200, published.text

        deleted = client.delete(f"/archival-objects/admin/{object_id}/canvases/{canvas_id}")
        assert deleted.status_code == 204, deleted.text
        assert client.get(f"/archival-objects/{object_id}/iiif/manifest").status_code == 404
        with factory() as db:
            old_asset = db.get(BookAsset, asset_id)
            assert old_asset is not None and old_asset.is_current is False
            event_row = db.scalar(select(PreservationEvent).where(
                PreservationEvent.archival_object_id == object_id,
                PreservationEvent.asset_id == asset_id,
                PreservationEvent.event_type == "access_withdrawn",
            ))
            assert event_row is not None
            assert event_row.checksum == old_asset.checksum_sha256
            obj = db.get(ArchivalObject, object_id)
            assert obj is not None and obj.rights is not None and obj.rights.verified_at is None
    finally:
        client.close()
        app.dependency_overrides.clear()
        engine.dispose()


def test_rights_approval_requires_evidence_reference(monkeypatch, tmp_path):
    client, _factory, engine = _client(monkeypatch, tmp_path)
    try:
        created = client.post(
            "/books/ingest",
            data={
                "material_type": "facsimile", "title": "Rights Evidence", "author": "Archive",
                "description": "A record used to test rights approval validation.", "rights_decision": "pending",
            },
            files=[("canvas_files", ("folio.png", _png_bytes((30, 100, 200)), "image/png"))],
        )
        assert created.status_code == 201, created.text
        object_id = created.json()["archival_object_id"]
        rejected = client.post(
            f"/archival-objects/admin/{object_id}/rights-review",
            json={"decision": "allow"},
        )
        assert rejected.status_code == 400
        assert "evidence source is required" in rejected.text
    finally:
        client.close()
        app.dependency_overrides.clear()
        engine.dispose()


def test_preservation_dashboard_returns_assets_copies_and_events_without_storage_keys(monkeypatch, tmp_path):
    client, _factory, engine = _client(monkeypatch, tmp_path)
    try:
        created = client.post(
            "/books/ingest",
            data={
                "material_type": "facsimile", "title": "Preservation Dashboard",
                "author": "Archive", "description": "Dashboard route contract test.",
                "rights_decision": "pending",
            },
            files=[("canvas_files", ("folio.png", _png_bytes((70, 110, 160)), "image/png"))],
        )
        assert created.status_code == 201, created.text
        object_id = created.json()["archival_object_id"]

        response = client.get(f"/preservation-events/admin/{object_id}/dashboard")
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["archival_object_id"] == object_id
        assert len(payload["assets"]) >= 1
        image_asset = next(asset for asset in payload["assets"] if asset["asset_type"] == "image")
        assert image_asset["logical_key"]
        assert image_asset["is_current"] is True
        assert image_asset["storage_locations"]
        location = image_asset["storage_locations"][0]
        assert location["asset_id"] == image_asset["id"]
        assert "storage_key" not in location
        assert "public_url" not in location
        assert any(event["event_type"] == "ingestion" for event in payload["events"])
        assert all("source_storage_key" not in event and "target_storage_key" not in event for event in payload["events"])

        missing = client.get("/preservation-events/admin/999999/dashboard")
        assert missing.status_code == 404
    finally:
        client.close()
        app.dependency_overrides.clear()
        engine.dispose()


def test_archival_metadata_and_provenance_can_be_edited_independently(monkeypatch, tmp_path):
    client, _factory, engine = _client(monkeypatch, tmp_path)
    try:
        created = client.post(
            "/books/ingest",
            data={
                "material_type": "facsimile", "title": "Metadata Editing",
                "author": "Archive", "description": "Initial catalogue description.",
                "rights_decision": "pending",
            },
            files=[("canvas_files", ("folio.png", _png_bytes((90, 40, 120)), "image/png"))],
        )
        assert created.status_code == 201, created.text
        object_id = created.json()["archival_object_id"]

        updated = client.patch(
            f"/archival-objects/admin/{object_id}",
            json={
                "identifier": "MS-2026-04",
                "object_type": "manuscript",
                "title": "Updated archival title",
                "description": "A separate archival description.",
                "metadata": {
                    "alternative_titles": ["Field Journal"],
                    "contributors": ["A. Researcher"],
                    "language": "en",
                    "subjects": ["field notes", "botany"],
                    "genre": ["journal"],
                    "publication_date": "1932-04-01",
                    "publisher": "Repository Press",
                    "edition": "First edition",
                    "external_identifier": "urn:test:1932-04",
                    "notes": "Descriptive metadata note.",
                },
                "provenance": {
                    "source_institution": "Coastal Archive",
                    "source_collection": "Field Records",
                    "shelfmark": "FR-4/2",
                    "accession_number": "ACC-44",
                    "original_format": "bound notebook",
                    "physical_condition": "Fragile cover",
                    "origin_place": "Kilifi",
                    "origin_date": "1932-04-01",
                    "digitized_by": "Archive Imaging Unit",
                    "digitized_at": "2026-11-10T09:00:00+03:00",
                    "digitization_method": "Overhead capture",
                    "scanner_device": "Camera rig 2",
                    "master_format": "TIFF",
                    "derivative_format": "JPEG",
                    "software": "Capture Station",
                    "notes": "Provenance note.",
                },
            },
        )
        assert updated.status_code == 200, updated.text
        payload = updated.json()
        assert payload["identifier"] == "MS-2026-04"
        assert payload["metadata"]["contributors"] == ["A. Researcher"]
        assert payload["metadata"]["publication_date"] == "1932-04-01"
        assert payload["provenance"]["source_institution"] == "Coastal Archive"
        assert payload["provenance"]["master_format"] == "TIFF"
    finally:
        client.close()
        app.dependency_overrides.clear()
        engine.dispose()
