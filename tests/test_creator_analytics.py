from app.schemas.creator_analytics import CreatorAnalyticsRead, CreatorBookAnalyticsRead
from app.services.creator_analytics import READER_ACTIVITY_WINDOW_DAYS


def test_creator_analytics_contract_contains_only_observable_metrics():
    analytics = CreatorAnalyticsRead(
        submission_count=2,
        submitted_count=1,
        under_review_count=1,
        changes_requested_count=0,
        hosted_book_count=1,
        active_paid_offer_count=1,
        lifetime_owner_count=3,
        reader_count=5,
        active_reader_count_30d=2,
        completed_reader_count=1,
        average_progress_percent=42.5,
        books=[],
    )
    assert analytics.reader_count == 5
    assert analytics.lifetime_owner_count == 3
    assert analytics.active_reader_count_30d == 2
    assert not hasattr(analytics, "revenue")
    assert not hasattr(analytics, "earnings")
    assert not hasattr(analytics, "conversion_rate")


def test_creator_book_analytics_contract_is_book_scoped():
    book = CreatorBookAnalyticsRead(
        hosted_book_id=4,
        book_id=19,
        title="Archive Test",
        status="hosted",
        reader_count=7,
        active_reader_count_30d=3,
        completed_reader_count=2,
        average_progress_percent=61.4,
        lifetime_owner_count=2,
        paid_offer_active=True,
    )
    assert book.book_id == 19
    assert book.paid_offer_active is True
    assert book.average_progress_percent == 61.4


def test_creator_analytics_activity_window_is_explicit():
    assert READER_ACTIVITY_WINDOW_DAYS == 30
