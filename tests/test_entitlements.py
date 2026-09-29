from datetime import datetime, timedelta, timezone

from app.models.entitlement import Entitlement
from app.services.entitlements import grant_book_entitlement


def test_entitlement_scope_vocabulary_is_explicit():
    assert Entitlement.__table_args__[0].name == "uq_entitlement_source"


def test_book_entitlement_fields_are_book_scoped():
    row = Entitlement(
        user_id=8,
        entitlement_type="book_access",
        book_id=12,
        source="lifetime_access",
        source_reference="creator_lifetime_access:44",
        status="active",
    )
    assert row.book_id == 12
    assert row.feature_key is None
    assert row.entitlement_type == "book_access"


def test_feature_entitlement_fields_are_feature_scoped():
    row = Entitlement(
        user_id=8,
        entitlement_type="feature_access",
        feature_key="advanced_reader",
        source="subscription",
        source_reference="subscription:basic:8",
        status="active",
    )
    assert row.feature_key == "advanced_reader"
    assert row.book_id is None


def test_book_grant_reactivates_same_source_reference():
    assert callable(grant_book_entitlement)
    start = datetime.now(timezone.utc)
    expiry = start + timedelta(days=30)
    assert expiry > start



def test_entitlement_model_can_be_persisted_and_resolved():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.models.book import Book
    from app.models.entitlement import Entitlement
    from app.models.user import User
    from app.core.database import Base
    from app.services.entitlements import resolve_book_access

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[User.__table__, Book.__table__, Entitlement.__table__])
    with Session(engine) as db:
        user = User(full_name="Reader", email="reader@example.com", password_hash="x")
        book = Book(
            title="Private Book",
            author="Author",
            cover="cover",
            description="Description",
            visibility="draft",
        )
        db.add_all([user, book])
        db.commit()
        db.refresh(user)
        db.refresh(book)

        allowed, reason, entitlement = resolve_book_access(db, user_id=user.id, book_id=book.id)
        assert allowed is False
        assert reason == "entitlement_required"
        assert entitlement is None

        book.visibility = "published"
        db.commit()
        allowed, reason, entitlement = resolve_book_access(db, user_id=user.id, book_id=book.id)
        assert allowed is True
        assert reason == "public"
        assert entitlement is None

        book.visibility = "draft"
        db.commit()

        grant_book_entitlement(
            db,
            user_id=user.id,
            book_id=book.id,
            source="admin",
            source_reference="manual-test:1",
        )
        db.commit()

        allowed, reason, entitlement = resolve_book_access(db, user_id=user.id, book_id=book.id)
        assert allowed is True
        assert reason == "entitled"
        assert entitlement is not None
