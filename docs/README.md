# The Librarian — Documentation

This folder is the authoritative documentation set for the Expo/React Native application.

## Read in this order

1. [ARCHITECTURE.md](./ARCHITECTURE.md) — product boundaries, app structure, API relationship, and access model.
2. [DEVELOPMENT.md](./DEVELOPMENT.md) — local setup, Expo SDK rules, verification, and checkpoint workflow.
3. [ROADMAP.md](./ROADMAP.md) — current sprint state and the next-work decision process.
4. [DOMAINS.md](./DOMAINS.md) — reader, archive, creator, community, and billing boundaries.
5. [CHECKPOINTS.md](./CHECKPOINTS.md) — condensed implementation history and important migrations/checkpoints.

The documentation intentionally does **not** keep one markdown file per tackle. Individual tackle notes became repetitive and quickly became stale. The checkpoint history below records the durable facts; the architecture and development documents describe the current system.

## Source of truth

- Product behavior: current application code and backend API contracts.
- Database evolution: Alembic migrations in the backend.
- Current work state: `ROADMAP.md`.
- Historical implementation record: `CHECKPOINTS.md`.

If documentation conflicts with executable code, verify the code/API contract before extending the feature and update the documentation as part of the same change.
