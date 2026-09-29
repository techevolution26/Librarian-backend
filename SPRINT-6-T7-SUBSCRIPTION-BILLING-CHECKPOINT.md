# Sprint 6 T7 — Subscription Billing Checkpoint

## Status

**T7 — Subscription Billing: COMPLETE**

## Boundary

T7 introduces real recurring subscription billing while preserving the product's existing domain boundaries:

- `SubscriptionPlan` remains catalogue metadata.
- `BillingCustomer` represents the provider customer identity.
- `Subscription` is the local projection of provider subscription state.
- `BillingWebhookEvent` provides webhook idempotency.
- Stripe is the billing source of truth.
- Webhook synchronization, not the checkout success redirect, changes local subscription state.
- T7 does not create purchase entitlements, book ownership, or creator revenue entries.
- Creator revenue and payout accounting remain separate from subscription billing.

## Stripe integration

Provider: Stripe sandbox.

The implementation supports:

- Stripe Customer creation with deterministic idempotency keys.
- Stripe-hosted Checkout in subscription mode.
- server-owned plan/price selection.
- request idempotency for Checkout Session creation.
- Stripe Customer Portal sessions.
- verified webhook signatures.
- subscription created/updated/deleted synchronization.
- checkout-session linkage.
- paid-invoice linkage.
- webhook event idempotency.
- effective subscription resolution for `active` and `trialing` subscriptions only.

The application does not trust a browser redirect as proof of payment.

## Database

Migration:

`d0e1f2a3b4c5_add_subscription_billing.py`

Adds:

- Stripe product/price identifiers to `subscription_plans`.
- `billing_customers`.
- `subscriptions`.
- `billing_webhook_events`.

Alembic head:

`d0e1f2a3b4c5`

## API

### Public/authenticated billing

- `GET /billing/subscription`
- `GET /billing/status`
- `POST /billing/checkout`
- `POST /billing/portal`

### Stripe

- `POST /billing/stripe/webhook`

### Plan mapping

Admin plan create/update can store:

- `stripe_product_id`
- `stripe_price_id`

Checkout accepts only the internal `plan_code`; clients cannot submit an arbitrary Stripe Price ID.

## Configuration

Add these environment variables in the real deployment environment:

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_SUCCESS_URL`
- `STRIPE_CANCEL_URL`
- `STRIPE_PORTAL_RETURN_URL`

The repository does not contain real Stripe secrets.

## Mobile-store boundary

The backend billing domain is provider-ready, but native mobile purchase UI is intentionally not added in T7. Stripe's current React Native subscription guidance notes that digital subscriptions consumed inside mobile apps can be subject to Apple/Google store billing rules. The web billing surface can therefore use Stripe Checkout while native purchase presentation remains a separate product/platform decision.

## Validation

- Focused T7 + existing subscription/entitlement/limit/creator regression suite: **58 passed**.
- `python -m compileall -q app tests`: **PASS**.
- Alembic head: **PASS — d0e1f2a3b4c5**.
- Migration revision IDs: **30 total / 30 unique**.
- ZIP integrity: **PASS**.
- Full FastAPI import/startup was **not claimed** in the isolated checkpoint because the environment is missing the existing `passlib` dependency. This is pre-existing environment incompleteness, not a T7 source error.

## Next boundary

T8 — Purchase Entitlements can consume verified billing/payment state without making Checkout, payment events, or subscriptions themselves equal to entitlements.
