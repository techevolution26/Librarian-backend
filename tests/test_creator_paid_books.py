from app.models.creator_paid_book import CREATOR_PAID_BOOK_STATUSES, CreatorPaidBook
from app.schemas.creator_paid_book import CreatorPaidBookCreate, CreatorPaidBookUpdate


def test_paid_book_status_vocabulary_is_explicit():
    assert CREATOR_PAID_BOOK_STATUSES == {"draft", "active", "archived"}


def test_paid_book_uses_minor_units_and_currency():
    row = CreatorPaidBook(
        id=1,
        hosted_book_id=7,
        creator_account_id=3,
        price_amount_minor=1299,
        currency="usd",
        status="draft",
    )
    assert row.price_amount_minor == 1299
    assert row.currency == "usd"


def test_paid_book_create_normalizes_currency_and_rejects_free_price():
    payload = CreatorPaidBookCreate(price_amount_minor=1299, currency=" KES ")
    assert payload.currency == "kes"

    try:
        CreatorPaidBookCreate(price_amount_minor=0, currency="KES")
    except Exception:
        pass
    else:
        raise AssertionError("zero-price paid offer must be rejected")


def test_paid_book_update_supports_archival_status():
    payload = CreatorPaidBookUpdate(status="archived", price_amount_minor=2500, currency="KES")
    assert payload.status == "archived"
    assert payload.price_amount_minor == 2500
    assert payload.currency == "kes"
