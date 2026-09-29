from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.bookmark import Bookmark
from app.models.note import Note
from app.models.notebook import Notebook
from app.models.subscription_plan import SubscriptionPlan
from app.models.subscription_plan_feature import SubscriptionPlanFeatureLimit
from app.models.user import User
from app.services.notebook_limits import (
    NOTEBOOK_NOTE_COUNT_FEATURE_KEY,
    get_notebook_note_count,
    get_notebook_note_limit_for_plan,
    notebook_limit_allows_note_creation,
)


def make_db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            SubscriptionPlan.__table__,
            SubscriptionPlanFeatureLimit.__table__,
            Notebook.__table__,
            Bookmark.__table__,
            Note.__table__,
        ],
    )
    return engine


def test_notebook_note_feature_key_is_distinct_from_bookmarks():
    assert NOTEBOOK_NOTE_COUNT_FEATURE_KEY == "notebook_note_count"
    assert NOTEBOOK_NOTE_COUNT_FEATURE_KEY != "bookmark_count"


def test_note_count_starts_at_zero():
    engine = make_db()
    with Session(engine) as db:
        user = User(full_name="Reader", email="reader@example.com", password_hash="x")
        db.add(user)
        db.commit()
        db.refresh(user)
        assert get_notebook_note_count(db, user_id=user.id) == 0


def test_note_count_counts_only_users_private_notebook_notes():
    engine = make_db()
    with Session(engine) as db:
        first = User(full_name="One", email="one@example.com", password_hash="x")
        second = User(full_name="Two", email="two@example.com", password_hash="x")
        db.add_all([first, second])
        db.commit()
        db.refresh(first)
        db.refresh(second)
        first_book = Notebook(user_id=first.id, title="One")
        second_book = Notebook(user_id=second.id, title="Two")
        db.add_all([first_book, second_book])
        db.commit()
        db.refresh(first_book)
        db.refresh(second_book)
        db.add_all([
            Note(notebook_id=first_book.id, body="a", title="A"),
            Note(notebook_id=first_book.id, body="b", title="B"),
            Note(notebook_id=second_book.id, body="c", title="C"),
        ])
        db.commit()
        assert get_notebook_note_count(db, user_id=first.id) == 2
        assert get_notebook_note_count(db, user_id=second.id) == 1


def make_plan(db: Session, *, limit_value: int | None, enabled: bool = True) -> SubscriptionPlan:
    plan = SubscriptionPlan(
        code="notebook-plan",
        name="Notebook Plan",
        description="",
        price_amount_minor=0,
        currency="usd",
        billing_interval="none",
        status="active",
        sort_order=1,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    db.add(SubscriptionPlanFeatureLimit(
        plan_id=plan.id,
        feature_key=NOTEBOOK_NOTE_COUNT_FEATURE_KEY,
        enabled=enabled,
        limit_value=limit_value,
    ))
    db.commit()
    return plan


def test_missing_policy_does_not_mean_unlimited():
    engine = make_db()
    with Session(engine) as db:
        user = User(full_name="Reader", email="reader@example.com", password_hash="x")
        plan = SubscriptionPlan(
            code="missing-policy",
            name="Missing Policy",
            description="",
            price_amount_minor=0,
            currency="usd",
            billing_interval="none",
            status="active",
            sort_order=1,
        )
        db.add_all([user, plan])
        db.commit()
        db.refresh(user)
        db.refresh(plan)
        allowed, count, limit = notebook_limit_allows_note_creation(db, user_id=user.id, plan_id=plan.id)
        assert allowed is False
        assert count == 0
        assert limit == 0


def test_finite_limit_allows_until_ceiling():
    engine = make_db()
    with Session(engine) as db:
        user = User(full_name="Reader", email="reader@example.com", password_hash="x")
        db.add(user)
        db.commit()
        db.refresh(user)
        plan = make_plan(db, limit_value=2)
        notebook = Notebook(user_id=user.id, title="My Notebook")
        db.add(notebook)
        db.commit()
        db.refresh(notebook)
        db.add(Note(notebook_id=notebook.id, body="a", title="A"))
        db.commit()
        allowed, count, limit = notebook_limit_allows_note_creation(db, user_id=user.id, plan_id=plan.id)
        assert (allowed, count, limit) == (True, 1, 2)
        db.add(Note(notebook_id=notebook.id, body="b", title="B"))
        db.commit()
        allowed, count, limit = notebook_limit_allows_note_creation(db, user_id=user.id, plan_id=plan.id)
        assert (allowed, count, limit) == (False, 2, 2)


def test_unlimited_policy_allows_note_creation():
    engine = make_db()
    with Session(engine) as db:
        user = User(full_name="Reader", email="reader@example.com", password_hash="x")
        db.add(user)
        db.commit()
        db.refresh(user)
        plan = make_plan(db, limit_value=None)
        allowed, count, limit = notebook_limit_allows_note_creation(db, user_id=user.id, plan_id=plan.id)
        assert (allowed, count, limit) == (True, 0, None)


def test_disabled_policy_blocks_note_creation():
    engine = make_db()
    with Session(engine) as db:
        user = User(full_name="Reader", email="reader@example.com", password_hash="x")
        db.add(user)
        db.commit()
        db.refresh(user)
        plan = make_plan(db, limit_value=None, enabled=False)
        allowed, count, limit = notebook_limit_allows_note_creation(db, user_id=user.id, plan_id=plan.id)
        assert (allowed, count, limit) == (False, 0, 0)


def test_limit_lookup_uses_notebook_note_count_key():
    engine = make_db()
    with Session(engine) as db:
        plan = make_plan(db, limit_value=25)
        resolved = get_notebook_note_limit_for_plan(db, plan_id=plan.id)
        assert resolved is not None
        assert resolved.feature_key == NOTEBOOK_NOTE_COUNT_FEATURE_KEY
        assert resolved.limit_value == 25
