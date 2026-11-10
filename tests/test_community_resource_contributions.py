from __future__ import annotations

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import Generator

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models.admin_activity_log import AdminActivityLog
from app.models.archival_canvas import ArchivalCanvas
from app.models.archival_object import ArchivalObject
from app.models.book import Book
from app.models.book_asset import BookAsset
from app.models.resource_contribution import ResourceContribution, ResourceContributionAsset
from app.models.notification import Notification
from app.services.notifications import create_notification, notification_manager
from app.models.user import User
from app.routes import books as books_route
from app.routes import resource_contributions as contributions_route
from app.services.storage import LocalStorageBackend


def _png_bytes(color: tuple[int, int, int]) -> bytes:
    output = BytesIO()
    Image.new("RGB", (32, 24), color).save(output, format="PNG")
    return output.getvalue()


def _client(monkeypatch, tmp_path):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    @event.listens_for(engine, "connect")
    def _register_sqlite_functions(connection, _record):
        connection.create_function("char_length", 1, len)

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as db:
        user = User(full_name="Community Member", email="member@example.test", password_hash="x", role="USER")
        other = User(full_name="Other Member", email="other@example.test", password_hash="x", role="USER")
        admin = User(full_name="Archive Admin", email="admin@example.test", password_hash="x", role="ADMIN")
        db.add_all([user, other, admin])
        db.commit()
        ids = {"user": user.id, "other": other.id, "admin": admin.id}

    active_user = {"id": ids["user"]}
    storage_root = tmp_path / "storage"
    (storage_root / "books").mkdir(parents=True)
    (storage_root / "covers").mkdir(parents=True)
    monkeypatch.setattr(contributions_route, "get_storage_root", lambda: storage_root)
    monkeypatch.setattr(contributions_route, "get_storage_backend", lambda: LocalStorageBackend(storage_root))
    monkeypatch.setattr(contributions_route, "get_settings", lambda: SimpleNamespace(
        max_pdf_upload_mb=10,
        max_text_upload_mb=10,
        max_archival_image_upload_mb=10,
        max_archival_canvas_count=20,
        max_archival_ingest_total_mb=50,
        max_pending_resource_contributions_per_user=5,
    ))
    monkeypatch.setattr(books_route, "BOOKS_STORAGE_DIR", storage_root / "books")

    def override_db() -> Generator[Session, None, None]:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    def override_user() -> User:
        with factory() as db:
            row = db.get(User, active_user["id"])
            assert row is not None
            return row

    monkeypatch.setitem(app.dependency_overrides, get_db, override_db)
    monkeypatch.setitem(app.dependency_overrides, get_current_user, override_user)
    client = TestClient(app)
    return client, factory, engine, active_user, ids, storage_root


def _submit_pdf(client: TestClient, title="Community Manuscript"):
    return client.post(
        "/community/resource-contributions/",
        data={
            "material_type": "pdf",
            "title": title,
            "author_name": "A. Contributor",
            "description": "A community-supplied historical source.",
            "language": "en",
            "genres": "History, Local records",
            "subjects": "Coastal history, Community memory",
            "original_format": "printed",
            "archival_object_type": "manuscript",
            "source_institution": "Community Archive",
            "shelfmark": "CA-17",
            "rights_statement": "all-rights-reserved",
            "rights_basis": "unknown",
            "accuracy_attested": "true",
        },
        files=[
            ("primary_file", ("source.pdf", b"%PDF-1.7\ncommunity test pdf", "application/pdf")),
            ("canvas_files", ("folio-1.png", _png_bytes((140, 60, 40)), "image/png")),
            ("canvas_files", ("folio-2.png", _png_bytes((40, 80, 140)), "image/png")),
        ],
    )


def test_any_authenticated_member_can_submit_private_multi_material_contribution(monkeypatch, tmp_path):
    client, factory, engine, active_user, ids, storage_root = _client(monkeypatch, tmp_path)
    try:
        response = _submit_pdf(client)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["status"] == "submitted"
        assert body["contributor_user_id"] == ids["user"]
        assert body["material_type"] == "pdf"
        mine = client.get("/community/resource-contributions/mine")
        assert mine.status_code == 200
        assert mine.json()["active_count"] == 1
        assert mine.json()["can_submit"] is True
        assert [item["asset_role"] for item in body["assets"]] == ["primary", "canvas", "canvas"]
        assert all("storage_key" not in item for item in body["assets"])

        with factory() as db:
            contribution = db.get(ResourceContribution, body["id"])
            assert contribution is not None
            assert len(contribution.assets) == 3
            assert db.scalar(select(Book.id).where(Book.title == "Community Manuscript")) is None
            assert db.scalar(select(ArchivalObject.id)) is None
            assert all((storage_root / asset.storage_key).is_file() for asset in contribution.assets)
            admin_notifications = db.scalars(select(Notification).where(Notification.user_id == ids["admin"])).all()
            assert any(item.type == "community.contribution.submitted" for item in admin_notifications)
            assert all(item.data_json["resource_contribution_id"] == body["id"] for item in admin_notifications)

        # The user cannot access another member's submission or the Admin queue.
        active_user["id"] = ids["other"]
        assert client.get(f"/community/resource-contributions/{body['id']}").status_code == 404
        assert client.get("/community/resource-contributions/admin/queue").status_code == 403
        # Ordinary users cannot bypass review through Admin ingestion.
        bypass = client.post("/books/ingest", data={"material_type": "pdf", "title": "No", "author": "No", "description": "No"}, files={"pdf_file": ("no.pdf", b"%PDF-1.4\n", "application/pdf")})
        assert bypass.status_code == 403
    finally:
        client.close()
        app.dependency_overrides.clear()
        engine.dispose()


def test_review_changes_and_resubmit_lifecycle(monkeypatch, tmp_path):
    client, factory, engine, active_user, ids, _ = _client(monkeypatch, tmp_path)
    try:
        created = _submit_pdf(client).json()
        active_user["id"] = ids["admin"]
        review = client.post(
            f"/community/resource-contributions/admin/{created['id']}/review",
            json={"status": "changes_requested", "review_note": "Please clarify the source institution."},
        )
        assert review.status_code == 200, review.text
        assert review.json()["status"] == "changes_requested"
        with factory() as db:
            audit = db.scalar(select(AdminActivityLog).where(AdminActivityLog.entity_type == "resource_contribution", AdminActivityLog.entity_id == created["id"]))
            assert audit is not None
            assert audit.action == "community.resource_contribution_changes_requested"
            contributor_notifications = db.scalars(select(Notification).where(Notification.user_id == ids["user"])).all()
            assert any(item.type == "community.contribution.changes_requested" for item in contributor_notifications)

        active_user["id"] = ids["user"]
        updated = client.patch(
            f"/community/resource-contributions/{created['id']}",
            json={"source_institution": "Regional Community Archive", "contributor_note": "Updated source details", "rights_basis": "permission_granted", "rights_statement": "cc-by", "rights_holder": "Regional Community Archive", "rights_evidence": "Permission record RC-2026-17", "original_format": "manuscript", "archival_object_type": "manuscript", "provenance_accession_number": "RC-17", "digitized_by": "Community Archive", "digitization_method": "Overhead capture"},
        )
        # The public contributor metadata editor intentionally accepts only its declared schema.
        assert updated.status_code == 200, updated.text
        assert updated.json()["rights_basis"] == "permission_granted"
        assert updated.json()["rights_statement"] == "cc-by"
        assert updated.json()["rights_evidence"] == "Permission record RC-2026-17"
        assert updated.json()["original_format"] == "manuscript"
        assert updated.json()["archival_object_type"] == "manuscript"
        assert updated.json()["provenance_accession_number"] == "RC-17"
        assert updated.json()["digitized_by"] == "Community Archive"
        resubmitted = client.post(f"/community/resource-contributions/{created['id']}/resubmit")
        assert resubmitted.status_code == 200, resubmitted.text
        assert resubmitted.json()["status"] == "submitted"
        with factory() as db:
            admin_notifications = db.scalars(select(Notification).where(Notification.user_id == ids["admin"])).all()
            assert any(item.type == "community.contribution.resubmitted" for item in admin_notifications)
    finally:
        client.close()
        app.dependency_overrides.clear()
        engine.dispose()


def test_admin_approval_imports_draft_and_keeps_rights_unreviewed_until_publish_gate(monkeypatch, tmp_path):
    client, factory, engine, active_user, ids, storage_root = _client(monkeypatch, tmp_path)
    try:
        created = _submit_pdf(client, "Approved Community Source").json()
        active_user["id"] = ids["admin"]
        response = client.post(f"/community/resource-contributions/admin/{created['id']}/approve")
        assert response.status_code == 200, response.text
        result = response.json()
        book_id = result["book_id"]
        object_id = result["archival_object_id"]
        assert result["book_visibility"] == "draft"
        assert result["rights_review_required"] is True

        with factory() as db:
            contribution = db.get(ResourceContribution, created["id"])
            book = db.get(Book, book_id)
            archival_object = db.get(ArchivalObject, object_id)
            assert contribution is not None and contribution.status == "approved"
            assert contribution.imported_book_id == book_id
            notifications = db.scalars(select(Notification).where(Notification.user_id == ids["user"])).all()
            approved_notifications = [item for item in notifications if item.type == "community.contribution.approved"]
            assert approved_notifications and approved_notifications[-1].data_json["book_id"] == book_id
            assert book is not None and book.visibility == "draft" and book.source_type == "pdf"
            assert archival_object is not None and archival_object.visibility == "draft"
            assert archival_object.rights is not None
            assert archival_object.rights.view_allowed is None
            assert archival_object.rights.verified_at is None
            canvases = db.scalars(select(ArchivalCanvas).where(ArchivalCanvas.archival_object_id == object_id).order_by(ArchivalCanvas.sequence)).all()
            assert len(canvases) == 2
            assets = db.scalars(select(BookAsset).where(BookAsset.book_id == book_id)).all()
            assert len(assets) == 3
            assert all(asset.uploaded_by == ids["user"] for asset in assets)
            assert all(asset.is_current for asset in assets)

        # Importing a contribution never publishes it or bypasses the rights review.
        blocked = client.patch(f"/books/{book_id}/publish")
        assert blocked.status_code == 409
        reviewed = client.post(
            f"/archival-objects/admin/{object_id}/rights-review",
            json={"decision": "allow", "rights_holder": "Community Archive", "rights_source": "Admin reviewed evidence"},
        )
        assert reviewed.status_code == 200, reviewed.text
        published = client.patch(f"/books/{book_id}/publish")
        assert published.status_code == 200, published.text
        assert published.json()["visibility"] == "published"
        contributor_view = client.get(f"/community/resource-contributions/{created['id']}")
        assert contributor_view.status_code == 200
        assert contributor_view.json()["imported_book_visibility"] == "published"
        assert contributor_view.json()["imported_book_archived"] is False
        with factory() as db:
            contributor_notifications = db.scalars(select(Notification).where(Notification.user_id == ids["user"])).all()
            publication_notifications = [item for item in contributor_notifications if item.type == "community.contribution.published"]
            assert publication_notifications
            assert publication_notifications[-1].data_json["book_id"] == book_id

        archived = client.patch(f"/books/{book_id}/archive")
        assert archived.status_code == 200, archived.text
        contributor_view = client.get(f"/community/resource-contributions/{created['id']}")
        assert contributor_view.status_code == 200
        assert contributor_view.json()["imported_book_archived"] is True
        restored = client.patch(f"/books/{book_id}/restore")
        assert restored.status_code == 200, restored.text
        contributor_view = client.get(f"/community/resource-contributions/{created['id']}")
        assert contributor_view.status_code == 200
        assert contributor_view.json()["imported_book_archived"] is False
        with factory() as db:
            contributor_notifications = db.scalars(select(Notification).where(Notification.user_id == ids["user"])).all()
            assert any(item.type == "community.contribution.archived" for item in contributor_notifications)
            assert any(item.type == "community.contribution.restored" for item in contributor_notifications)

        # Re-approval cannot duplicate the catalogue record.
        duplicate = client.post(f"/community/resource-contributions/admin/{created['id']}/approve")
        assert duplicate.status_code == 409
    finally:
        client.close()
        app.dependency_overrides.clear()
        engine.dispose()


def test_non_pdf_text_contribution_is_supported_and_private(monkeypatch, tmp_path):
    client, factory, engine, active_user, ids, storage_root = _client(monkeypatch, tmp_path)
    try:
        response = client.post(
            "/community/resource-contributions/",
            data={
                "material_type": "text",
                "title": "Community transcription",
                "author_name": "Community contributor",
                "description": "A verified UTF-8 transcription candidate.",
                "rights_basis": "unknown",
                "accuracy_attested": "true",
            },
            files={"primary_file": ("source.txt", "First line\nSecond line".encode(), "text/plain")},
        )
        assert response.status_code == 201, response.text
        assert response.json()["material_type"] == "text"
        assert len(response.json()["assets"]) == 1
        with factory() as db:
            assert db.scalar(select(Book.id).where(Book.title == "Community transcription")) is None
    finally:
        client.close()
        app.dependency_overrides.clear()
        engine.dispose()


def test_contribution_asset_preview_is_private_and_admin_queue_is_access_controlled(monkeypatch, tmp_path):
    client, factory, engine, active_user, ids, _ = _client(monkeypatch, tmp_path)
    try:
        created_response = _submit_pdf(client, "Private preview source")
        assert created_response.status_code == 201, created_response.text
        created = created_response.json()
        primary = next(asset for asset in created["assets"] if asset["asset_role"] == "primary")

        owner_preview = client.get(f"/community/resource-contributions/{created['id']}/assets/{primary['id']}")
        assert owner_preview.status_code == 200
        assert owner_preview.content.startswith(b"%PDF-")
        assert owner_preview.headers.get("content-disposition", "").startswith("inline")

        active_user["id"] = ids["other"]
        denied_preview = client.get(f"/community/resource-contributions/{created['id']}/assets/{primary['id']}")
        assert denied_preview.status_code == 404
        denied_approval = client.post(f"/community/resource-contributions/admin/{created['id']}/approve")
        assert denied_approval.status_code == 403

        active_user["id"] = ids["admin"]
        queue = client.get("/community/resource-contributions/admin/queue?status=submitted")
        assert queue.status_code == 200, queue.text
        assert queue.json()["total"] == 1
        admin_preview = client.get(f"/community/resource-contributions/{created['id']}/assets/{primary['id']}")
        assert admin_preview.status_code == 200
    finally:
        client.close()
        app.dependency_overrides.clear()
        engine.dispose()


def test_image_only_facsimile_submission_imports_ordered_canvas_assets(monkeypatch, tmp_path):
    client, factory, engine, active_user, ids, storage_root = _client(monkeypatch, tmp_path)
    try:
        response = client.post(
            "/community/resource-contributions/",
            data={
                "material_type": "facsimile", "title": "Community Scan Sequence", "author_name": "Unknown community creator",
                "description": "An image-only sequence contributed for archival review.", "language": "und",
                "original_format": "manuscript", "archival_object_type": "manuscript",
                "rights_statement": "restricted", "rights_basis": "unknown", "accuracy_attested": "true",
            },
            files=[
                ("canvas_files", ("scan-01.png", _png_bytes((20, 90, 150)), "image/png")),
                ("canvas_files", ("scan-02.png", _png_bytes((150, 90, 20)), "image/png")),
            ],
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["material_type"] == "facsimile"
        assert [asset["sequence"] for asset in body["assets"]] == [1, 2]
        assert all(asset["asset_role"] == "canvas" for asset in body["assets"])
        active_user["id"] = ids["admin"]
        approved = client.post(f"/community/resource-contributions/admin/{body['id']}/approve")
        assert approved.status_code == 200, approved.text
        with factory() as db:
            book = db.get(Book, approved.json()["book_id"])
            assert book is not None and book.source_type == "iiif" and book.visibility == "draft"
            canvases = db.scalars(select(ArchivalCanvas).where(ArchivalCanvas.archival_object_id == approved.json()["archival_object_id"]).order_by(ArchivalCanvas.sequence)).all()
            assert len(canvases) == 2
            assert [canvas.sequence for canvas in canvases] == [1, 2]
    finally:
        client.close()
        app.dependency_overrides.clear()
        engine.dispose()


def test_notification_realtime_delivery_waits_for_commit(monkeypatch, tmp_path):
    client, factory, engine, active_user, ids, _ = _client(monkeypatch, tmp_path)
    published = []
    monkeypatch.setattr(notification_manager, "publish", lambda user_id, payload: published.append((user_id, payload)))
    try:
        with factory() as db:
            create_notification(
                db, user_id=ids["user"], type="community.contribution.test",
                title="Test", body="Must not be delivered before commit.",
            )
            assert published == []
            db.rollback()
        with factory() as db:
            create_notification(
                db, user_id=ids["user"], type="community.contribution.test",
                title="Test", body="Delivered after commit.",
            )
            assert published == []
            db.commit()
            assert len(published) == 1
            assert published[0][0] == ids["user"]
            assert published[0][1]["notification"]["title"] == "Test"
    finally:
        client.close()
        app.dependency_overrides.clear()
        engine.dispose()


def test_under_review_contribution_is_locked_for_contributor(monkeypatch, tmp_path):
    client, factory, engine, active_user, ids, _ = _client(monkeypatch, tmp_path)
    try:
        created = _submit_pdf(client, "Locked while reviewed").json()
        active_user["id"] = ids["admin"]
        reviewed = client.post(
            f"/community/resource-contributions/admin/{created['id']}/review",
            json={"status": "under_review", "review_note": "Review started."},
        )
        assert reviewed.status_code == 200
        duplicate_review = client.post(
            f"/community/resource-contributions/admin/{created['id']}/review",
            json={"status": "under_review", "review_note": "Duplicate review should not notify twice."},
        )
        assert duplicate_review.status_code == 409
        active_user["id"] = ids["user"]
        update = client.patch(f"/community/resource-contributions/{created['id']}", json={"description": "Attempted edit"})
        withdraw = client.post(f"/community/resource-contributions/{created['id']}/withdraw")
        assert update.status_code == 409
        assert withdraw.status_code == 409
        with factory() as db:
            assert db.scalar(select(ResourceContribution.status).where(ResourceContribution.id == created["id"])) == "under_review"
            notifications = db.scalars(select(Notification).where(Notification.user_id == ids["user"])).all()
            assert any(item.type == "community.contribution.under_review" for item in notifications)
    finally:
        client.close()
        app.dependency_overrides.clear()
        engine.dispose()


def test_book_asset_public_url_is_nullable_for_private_storage_assets():
    assert BookAsset.__table__.c.public_url.nullable is True

