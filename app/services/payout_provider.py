from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PayoutSubmission:
    provider_payout_id: str | None
    provider_reference: str | None


class PayoutProvider(Protocol):
    """Provider boundary for future real payout integrations.

    T10 deliberately defines the seam without calling an external payment
    provider. A later provider integration must use CreatorPayout's stable
    provider_idempotency_key when submitting money.
    """

    def submit(self, *, amount_minor: int, currency: str, idempotency_key: str) -> PayoutSubmission:
        ...
