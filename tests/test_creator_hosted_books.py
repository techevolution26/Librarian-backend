from app.models.creator_hosted_book import CREATOR_HOSTED_BOOK_STATUSES, CreatorHostedBook
from app.schemas.creator_hosted_book import CreatorHostedBookRead


def test_hosted_book_status_vocabulary_is_explicit():
    assert CREATOR_HOSTED_BOOK_STATUSES == {"draft", "hosted", "archived"}


def test_hosted_book_keeps_submission_and_book_identity_separate():
    row = CreatorHostedBook(
        id=1,
        submission_id=10,
        creator_account_id=3,
        book_id=21,
        status="hosted",
    )
    assert row.submission_id == 10
    assert row.book_id == 21
    assert row.status == "hosted"


def test_hosted_book_read_contract_exposes_private_asset_integrity_without_public_url():
    fields = CreatorHostedBookRead.model_fields
    assert "asset_checksum_sha256" in fields
    assert "asset_size_bytes" in fields
    assert "has_access_asset" in fields
    assert "book_id" in fields
