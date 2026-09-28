from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.models.creator_revenue_ledger import CREATOR_REVENUE_ENTRY_TYPES, CreatorRevenueLedgerEntry
from app.schemas.creator_revenue import CreatorRevenueRecordCreate
from app.services.creator_revenue import build_creator_revenue_summary, record_verified_revenue_event


def payload(**overrides):
    data = {
        "paid_offer_id": 11,
        "buyer_user_id": 22,
        "gross_amount_minor": 1299,
        "creator_share_minor": 1000,
        "platform_share_minor": 299,
        "currency": " KES ",
        "provider": "stripe",
        "provider_event_id": "evt_123",
        "provider_reference": "pi_123",
        "occurred_at": datetime.now(timezone.utc),
    }
    data.update(overrides)
    return CreatorRevenueRecordCreate(**data)


def test_revenue_entry_type_vocabulary_is_explicit():
    assert CREATOR_REVENUE_ENTRY_TYPES == {"sale", "reversal", "adjustment"}


def test_revenue_payload_normalizes_currency_and_requires_balanced_shares():
    row = payload()
    assert row.currency == "kes"

    class DB:
        def scalar(self, query):
            return None

    with pytest.raises(Exception, match="shares must equal gross"):
        record_verified_revenue_event(DB(), payload(platform_share_minor=300))


def test_revenue_model_has_immutable_audit_fields():
    row = CreatorRevenueLedgerEntry(
        creator_account_id=1,
        hosted_book_id=2,
        paid_offer_id=3,
        entry_type="sale",
        gross_amount_minor=1299,
        creator_share_minor=1000,
        platform_share_minor=299,
        currency="kes",
        provider="stripe",
        provider_event_id="evt_123",
        occurred_at=datetime.now(timezone.utc),
    )
    assert row.provider_event_id == "evt_123"
    assert row.recorded_at is None


def test_record_verified_event_is_idempotent():
    existing = CreatorRevenueLedgerEntry(id=7, provider="stripe", provider_event_id="evt_123")

    class DB:
        def scalar(self, query):
            return existing

    result = record_verified_revenue_event(DB(), payload())
    assert result is existing


def test_record_verified_event_rejects_unbalanced_shares_before_storage():
    class DB:
        def scalar(self, query):
            return None

    with pytest.raises(Exception, match="shares must equal gross"):
        record_verified_revenue_event(DB(), payload(platform_share_minor=300))


def test_record_verified_event_requires_active_offer_and_hosted_book():
    class DB:
        def __init__(self):
            self.offer = SimpleNamespace(id=11, hosted_book_id=12, creator_account_id=4, status="draft", currency="kes")

        def scalar(self, query):
            return None

        def get(self, model, ident):
            if ident == 11:
                return self.offer
            return SimpleNamespace(status="hosted")

    with pytest.raises(Exception, match="Only active paid offers"):
        record_verified_revenue_event(DB(), payload())


def test_revenue_summary_uses_compensating_entries_without_mutating_ledger():
    sale = CreatorRevenueLedgerEntry(
        id=1, creator_account_id=4, hosted_book_id=12, paid_offer_id=11,
        entry_type="sale", gross_amount_minor=1299, creator_share_minor=1000,
        platform_share_minor=299, currency="kes", provider="stripe",
        provider_event_id="evt_sale", occurred_at=datetime.now(timezone.utc),
    )
    now = datetime.now(timezone.utc)
    sale.recorded_at = now
    sale.created_at = now
    reversal = CreatorRevenueLedgerEntry(
        id=2, creator_account_id=4, hosted_book_id=12, paid_offer_id=11,
        entry_type="reversal", gross_amount_minor=1299, creator_share_minor=1000,
        platform_share_minor=299, currency="kes", provider="stripe",
        provider_event_id="evt_reversal", occurred_at=now, recorded_at=now, created_at=now,
    )

    class Result:
        def all(self):
            return [reversal, sale]

    class DB:
        def scalars(self, query):
            return Result()

    summary = build_creator_revenue_summary(DB(), 4)
    assert summary.entry_count == 2
    assert summary.gross_amount_minor == 0
    assert summary.creator_share_minor == 0
    assert summary.platform_share_minor == 0
    assert sale.gross_amount_minor == 1299
    assert reversal.gross_amount_minor == 1299
