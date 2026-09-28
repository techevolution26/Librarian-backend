# The Librarian — Sprint 5 T3 Author Book Submission Checkpoint

## Implemented

- Creator-owned `CreatorBookSubmission` model, separate from public/admin `Book`.
- Draft → submitted → under_review / changes_requested lifecycle.
- Creator CRUD for draft and changes-requested submissions.
- Explicit submit action.
- Admin review queue for submitted/under-review records.
- Admin review action can move a submission to `under_review` or `changes_requested` with an auditable reviewer and note.
- CreatorAccount remains the sole creator identity model.
- No automatic Book creation or publication.
- No rights declaration, pricing, entitlement, hosting, revenue, or payout logic introduced.

## API

Creator:
- `GET /creator/submissions/`
- `POST /creator/submissions/`
- `GET /creator/submissions/{submission_id}`
- `PATCH /creator/submissions/{submission_id}`
- `POST /creator/submissions/{submission_id}/submit`

Admin:
- `GET /creator/submissions/admin/queue?status=submitted`
- `POST /creator/submissions/admin/{submission_id}/review`

## Validation

- `python -m compileall -q app tests` — PASS
- `alembic heads` — `f1a2b3c4d5e6 (head)`
- Targeted regression suite — `12 passed`
- Native deterministic regression checks — PASS
- Native full TypeScript check — NOT RUN; `node_modules` is intentionally absent from the checkpoint.
- Full production database/runtime integration — NOT CLAIMED.
