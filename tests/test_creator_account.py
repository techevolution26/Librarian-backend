from app.models.creator_account import CreatorAccount
from app.schemas.creator import CreatorAccountCreate, CreatorAccountUpdate


def test_creator_account_schema_and_identity_contract() -> None:
    create = CreatorAccountCreate(
        display_name="Jane Writer",
        slug="jane-writer",
        bio="A reader and author.",
        website_url="https://example.com",
    )
    assert create.slug == "jane-writer"
    assert str(create.website_url) == "https://example.com/"

    update = CreatorAccountUpdate(bio=None, website_url=None, is_public=False)
    assert "bio" in update.model_fields_set
    assert "website_url" in update.model_fields_set
    assert update.is_public is False

    assert CreatorAccount.__tablename__ == "creator_accounts"
    assert CreatorAccount.user_id.property.columns[0].nullable is False
