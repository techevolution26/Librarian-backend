# Sanitization notes

This delivery removes committed local secrets and MySQL-specific development artifacts,
moves the backend to PostgreSQL, adds Compose Watch, and fixes several correctness/security
issues found during the audit.

Important: the original archive contained a live `.env` with a database password and JWT
secret. Those credentials must be considered exposed and rotated even though the sanitized
copy no longer contains them.

Key fixes:
- PostgreSQL + Psycopg 3 instead of MySQL + PyMySQL.
- Removed legacy root `models.py` and duplicate `requirments.txt`.
- Added `.env.example` and `.gitignore`.
- Added Compose Watch with `sync` for application code and `rebuild` for dependency/image changes.
- Health endpoint now checks database connectivity.
- JWT expiry now respects `ACCESS_TOKEN_EXPIRE_MINUTES`.
- Avatar uploads now have a size limit and centralized file validation.
- Public book content now respects published/non-archived visibility.
- Circle progress updates verify that the referenced circle book belongs to the circle and matches the user's library book.
- Mobile signup now follows the actual backend OpenAPI contract (signup, then login).
- Mobile library progress bar now treats progress as 0–100 instead of multiplying it by 100.
