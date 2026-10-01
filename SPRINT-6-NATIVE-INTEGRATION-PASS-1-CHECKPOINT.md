# The Librarian — Sprint 6 Native Integration Pass 1

## Scope
This checkpoint aligns the native Expo client with the existing Sprint 6 subscription/access capabilities.

### Native surfaces added
- Subscription plan catalogue
- Subscription/billing status and provider portal
- Entitlement/access authority screen
- Purchase history
- Public creator paid-offer discovery and checkout entry
- Advanced reader capability catalogue
- Institutional membership/effective institutional access
- Profile navigation entry points for the above
- Book-detail backend access decision display

### API contract additions
- `/plans`
- `/billing/status`
- `/billing/subscription`
- `/billing/checkout`
- `/billing/portal`
- `/entitlements/mine`
- `/entitlements/books/{book_id}/access`
- `/purchases/mine`
- `/purchases/books/{paid_offer_id}/checkout`
- `/reader/capabilities/{plan_code}`
- `/institutions/mine`
- `/institutions/effective-subscription`
- institution membership/plan reads and mutations supported by the existing backend contract

### Backend contract repair
The public creator catalogue previously exposed published books but did not expose an active `CreatorPaidBook` identifier. The public creator response now includes:
- `paid_offer_id`
- `price_amount_minor`
- `currency`

Only active paid offers attached to hosted, published, non-archived creator books are exposed.

No migration was required.

## Validation
- Backend `python3 -m compileall -q app tests`: PASS
- Alembic head: `d1e2f3a4b5c6`: PASS
- Migration revision uniqueness: 33 revisions, no duplicates: PASS
- Native TypeScript syntax check: no syntax errors were emitted before dependency/configuration errors.
- Full native `tsc` NOT claimed: checkpoint excludes `node_modules`, and the isolated environment lacks Expo/React type dependencies and `expo/tsconfig.base`.
- Focused backend pytest NOT claimed: isolated environment lacks the existing `passlib` dependency during route import/collection.
- ZIP integrity: verified after creation.

## Architectural boundaries preserved
- Plan catalogue is not a subscription.
- Subscription is not a purchase.
- Purchase is not an entitlement.
- Lifetime ownership remains distinct from purchase transactions.
- Entitlement state remains backend-authoritative.
- Checkout redirects do not grant access directly.
- Institutional access remains membership + institution subscription based.
- No fake prices, purchases, revenue, payouts, or entitlements were created.
