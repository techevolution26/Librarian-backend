from datetime import datetime, timezone

from app.models.creator_account import CreatorAccount
from app.models.creator_book_submission import CreatorBookSubmission
from app.services.creator import build_creator_dashboard


def test_creator_submission_genres_round_trip():
    row = CreatorBookSubmission(
        creator_account_id=1,
        title="Archive Test",
        author_name="Author Test",
        description="Description",
        language="en",
        genre_csv="History, Literature, History",
        status="draft",
    )
    assert row.genres == ["History", "Literature", "History"]
    row.genres = ["History", " Literature ", ""]
    assert row.genre_csv == "History,Literature"


def test_creator_dashboard_uses_existing_account_only():
    account = CreatorAccount(
        id=1,
        user_id=1,
        display_name="Test Creator",
        slug="test-creator",
        bio="A creator",
        website_url="https://example.com",
        profile_image_url="https://example.com/avatar.png",
        status="active",
        is_public=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    result = build_creator_dashboard(account)
    assert result.profile_complete is True
    assert result.profile_completion_percent == 100
    assert result.missing_profile_fields == []


def test_submission_review_status_vocabulary_is_explicit():
    from app.models.creator_book_submission import CREATOR_SUBMISSION_STATUSES

    assert CREATOR_SUBMISSION_STATUSES == {
        "draft",
        "submitted",
        "under_review",
        "changes_requested",
    }
