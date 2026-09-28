# Sprint 5 T10 — Payout System Checkpoint

## Status

- Sprint 5 T10 — **Payout System**: complete
- Scope intentionally stops at payout eligibility, durable payout records, reservation/allocation, lifecycle state, idempotency, and provider boundary.
- No real payment/payout provider is called by this tackle.

## Architecture

```text
Creator Revenue Ledger
        ↓
Currency-specific eligible balance
        ↓
Payout request + idempotency
        ↓
CreatorPayout
        ↓
CreatorPayoutAllocation
        ↓
Provider-neutral payout boundary
        ↓
requested → approved → processing → paid
                         ↘ failed → retry
              requested/approved → cancelled
```

## Backend

Added:

- `CreatorPayout`
  - creator account
  - currency
  - requested and eligibility snapshots
  - lifecycle status
  - provider-neutral identifiers
  - stable provider idempotency key
  - creator request idempotency key
  - attempt count
  - failure code/message
  - lifecycle timestamps
- `CreatorPayoutAllocation`
  - reserves creator ledger shares without mutating immutable revenue entries
  - supports partial allocation of a positive ledger entry
  - failed/cancelled payouts release their allocation back to eligibility
- currency-specific eligibility calculation
- negative carry-forward from reversal/adjustment entries
- creator payout request endpoint
- creator payout overview endpoint
- admin lifecycle endpoints for approve/process/complete/fail/retry/cancel
- provider-neutral `PayoutProvider` protocol seam
- migration `f3a4b5c6d7e8`

### Safeguards

- provider/idempotency boundary prevents duplicate request creation
- payout requests cannot exceed the current eligible balance
- currencies are never aggregated together
- only positive sale/adjustment creator shares are allocatable
- reversals/adjustments remain accounting entries and reduce eligibility
- failed/cancelled payout reservations are not treated as settled
- failed retry re-checks current eligibility before returning to processing
- payout state transitions are explicit
- real provider execution is not performed by T10

## Native

Added:

- `app/creator-payouts.tsx`
  - currency-specific eligible balances
  - payout request flow
  - payout history/status
  - failure visibility
  - explicit separation between accounting and payout execution
- `lib/api.ts`
  - payout types
  - payout overview request
  - payout request API
- creator dashboard payout entry point

Native idempotency keys are retained across a failed request attempt so a retry can reuse the same request identity.

## Validation

- T9 revenue tests + T10 payout tests: **16 passed**
- backend `compileall`: **PASS**
- Alembic heads: **single head `f3a4b5c6d7e8`**
- native source contract checks: **PASS**
- full native TypeScript: **not claimed** — checkpoint intentionally excludes `node_modules`; isolated `tsc` cannot resolve the Expo base config and packages
- full FastAPI runtime/startup: **not claimed** — isolated environment has existing dependency/configuration limitations

## Boundary preserved

T10 does **not** introduce:

- Stripe checkout/payment processing
- automatic money transfer
- external payout API calls
- entitlement creation
- subscription billing
- creator public domain/profile

Those remain separate concerns.
