from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.models.creator_payout import CreatorPayout
from app.models.creator_revenue_ledger import CreatorRevenueLedgerEntry
from app.schemas.creator_payout import CreatorPayoutRequest
from app.services.creator_payout import (
    ACTIVE_PAYOUT_STATUSES,
    approve_creator_payout,
    begin_creator_payout,
    cancel_creator_payout,
    fail_creator_payout,
    get_creator_payout_balances,
)


class Result:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class ScalarResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class DB:
    def __init__(self, *, scalars=None, execute=None, scalar=None):
        self._scalars = list(scalars or [])
        self._execute = list(execute or [])
        self._scalar = list(scalar or [])
        self.added = []

    def scalars(self, _query):
        return ScalarResult(self._scalars.pop(0))

    def execute(self, _query):
        return Result(self._execute.pop(0))

    def scalar(self, _query):
        return self._scalar.pop(0)

    def add(self, value):
        self.added.append(value)

    def flush(self):
        for value in self.added:
            if isinstance(value, CreatorPayout):
                value.id = 91

    def commit(self):
        pass

    def refresh(self, _value):
        pass


def entry(entry_id, amount, currency="kes", entry_type="sale"):
    now = datetime.now(timezone.utc)
    return CreatorRevenueLedgerEntry(
        id=entry_id,
        creator_account_id=4,
        hosted_book_id=12,
        paid_offer_id=11,
        entry_type=entry_type,
        gross_amount_minor=amount,
        creator_share_minor=amount,
        platform_share_minor=0,
        currency=currency,
        provider="stripe",
        provider_event_id=f"evt_{entry_id}",
        occurred_at=now,
        recorded_at=now,
        created_at=now,
    )


def test_payout_request_schema_normalizes_currency_and_requires_key():
    payload = CreatorPayoutRequest(currency=" KES ", amount_minor=1000, idempotency_key="request-123")
    assert payload.currency == "kes"
    with pytest.raises(ValueError):
        CreatorPayoutRequest(currency="kes", amount_minor=1000, idempotency_key="short")


def test_payout_balance_is_currency_specific_and_respects_active_reservations():
    db = DB(
        scalars=[[entry(1, 1500), entry(2, 500, entry_type="reversal"), entry(3, 900, currency="usd")]],
        execute=[[('kes', 400)]],
    )
    balances = get_creator_payout_balances(db, 4)
    assert balances == [
        {"currency": "kes", "ledger_creator_share_minor": 1000, "allocated_active_minor": 400, "eligible_balance_minor": 600},
        {"currency": "usd", "ledger_creator_share_minor": 900, "allocated_active_minor": 0, "eligible_balance_minor": 900},
    ]


def test_active_statuses_reserve_balance_but_failed_and_cancelled_release_it():
    assert ACTIVE_PAYOUT_STATUSES == {"requested", "approved", "processing", "paid"}


def payout(status="requested"):
    now = datetime.now(timezone.utc)
    return CreatorPayout(
        id=7,
        creator_account_id=4,
        currency="kes",
        requested_amount_minor=500,
        eligible_amount_minor=800,
        status=status,
        provider_idempotency_key="librarian-payout-7",
        idempotency_key="request-123456",
        requested_at=now,
        created_at=now,
        updated_at=now,
    )


def test_approval_only_accepts_requested_payout():
    row = payout()
    db = DB(scalar=[row])
    result = approve_creator_payout(db, 7)
    assert result.status == "approved"
    assert result.approved_at is not None


def test_processing_increments_attempt_and_records_provider():
    row = payout("approved")
    db = DB(scalar=[row])
    result = begin_creator_payout(db, 7, "manual")
    assert result.status == "processing"
    assert result.provider == "manual"
    assert result.attempt_count == 1
    assert result.processing_at is not None


def test_failed_payout_retains_failure_for_retry():
    row = payout("processing")
    db = DB(scalar=[row])
    result = fail_creator_payout(db, 7, "bank_unavailable", "Destination account could not be reached")
    assert result.status == "failed"
    assert result.failure_code == "bank_unavailable"
    assert result.failure_message == "Destination account could not be reached"
    assert result.failed_at is not None


def test_cancel_only_accepts_pre_processing_states():
    row = payout("approved")
    db = DB(scalar=[row])
    result = cancel_creator_payout(db, 7)
    assert result.status == "cancelled"
    assert result.cancelled_at is not None


def test_failed_retry_checks_current_eligible_balance():
    row = payout("failed")
    db = DB(
        scalar=[row],
        scalars=[[entry(1, 200)]],
        execute=[[('kes', 0)]],
    )
    with pytest.raises(Exception, match="eligible balance is insufficient"):
        begin_creator_payout(db, 7, "manual")


def test_payout_request_reserves_only_requested_amount_from_positive_ledger_shares():
    db = DB(
        scalars=[
            [entry(1, 1000), entry(2, 200, entry_type="reversal")],
            [entry(1, 1000)],
        ],
        execute=[[('kes', 0)], []],
        scalar=[None, SimpleNamespace(id=4)],
    )
    from app.services.creator_payout import request_creator_payout

    result = request_creator_payout(
        db,
        creator_account_id=4,
        currency="kes",
        amount_minor=600,
        idempotency_key="request-123456",
    )
    allocations = [item for item in db.added if item.__class__.__name__ == "CreatorPayoutAllocation"]
    assert result.status == "requested"
    assert result.eligible_amount_minor == 800
    assert len(allocations) == 1
    assert allocations[0].allocated_amount_minor == 600
