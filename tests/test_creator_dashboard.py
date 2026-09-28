from datetime import datetime, timezone

from app.models.creator_account import CreatorAccount
from app.schemas.creator import CreatorDashboardRead
from app.services.creator import build_creator_dashboard


def make_account(**overrides):
    values = {
        "id": 1,
        "user_id": 7,
        "display_name": "Archive Studio",
        "slug": "archive-studio",
        "bio": "Preserving and publishing cultural memory.",
        "website_url": "https://example.com",
        "profile_image_url": "https://example.com/profile.jpg",
        "status": "active",
        "is_public": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    values.update(overrides)
    return CreatorAccount(**values)


def test_creator_dashboard_reports_complete_profile():
    result = build_creator_dashboard(make_account())

    assert isinstance(result, CreatorDashboardRead)
    assert result.profile_completion_percent == 100
    assert result.profile_complete is True
    assert result.missing_profile_fields == []


def test_creator_dashboard_reports_missing_optional_profile_fields():
    result = build_creator_dashboard(
        make_account(
            bio=None,
            website_url=None,
            profile_image_url=None,
        )
    )

    assert result.profile_completion_percent == 40
    assert result.profile_complete is False
    assert result.missing_profile_fields == [
        "bio",
        "website_url",
        "profile_image_url",
    ]
