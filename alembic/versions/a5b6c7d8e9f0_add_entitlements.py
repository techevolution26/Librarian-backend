"""add entitlement engine foundation

Revision ID: a5b6c7d8e9f0
Revises: f3a4b5c6d7e8
"""
from alembic import op
import sqlalchemy as sa

revision = "a5b6c7d8e9f0"
down_revision = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "entitlements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("entitlement_type", sa.String(length=30), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=True),
        sa.Column("feature_key", sa.String(length=100), nullable=True),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("source_reference", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "(entitlement_type = 'book_access' AND book_id IS NOT NULL AND feature_key IS NULL) "
            "OR (entitlement_type = 'feature_access' AND book_id IS NULL AND feature_key IS NOT NULL)",
            name="ck_entitlement_scope_matches_type",
        ),
        sa.CheckConstraint(
            "expires_at IS NULL OR expires_at > starts_at",
            name="ck_entitlement_expiry_after_start",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "entitlement_type", "book_id", "feature_key", "source", "source_reference",
            name="uq_entitlement_source",
        ),
    )
    op.create_index("ix_entitlements_id", "entitlements", ["id"], unique=False)
    op.create_index("ix_entitlements_user_id", "entitlements", ["user_id"], unique=False)
    op.create_index("ix_entitlements_book_id", "entitlements", ["book_id"], unique=False)
    op.create_index("ix_entitlements_feature_key", "entitlements", ["feature_key"], unique=False)
    op.create_index("ix_entitlements_status", "entitlements", ["status"], unique=False)

    # Materialize all existing active lifetime ownership as authoritative
    # entitlement rows. The source reference preserves traceability without
    # coupling the generic entitlement table to creator-specific tables.
    op.execute(
        sa.text(
            """
            INSERT INTO entitlements
                (user_id, entitlement_type, book_id, feature_key, source, source_reference,
                 status, starts_at, expires_at, revoked_at, created_at, updated_at)
            SELECT
                cla.user_id,
                'book_access',
                chb.book_id,
                NULL,
                'lifetime_access',
                'creator_lifetime_access:' || CAST(cla.id AS VARCHAR(255)),
                'active',
                cla.granted_at,
                NULL,
                NULL,
                cla.created_at,
                cla.updated_at
            FROM creator_lifetime_access cla
            JOIN creator_hosted_books chb ON chb.id = cla.hosted_book_id
            WHERE cla.status = 'active'
            """
        )
    )


def downgrade() -> None:
    for name in (
        "ix_entitlements_status",
        "ix_entitlements_feature_key",
        "ix_entitlements_book_id",
        "ix_entitlements_user_id",
        "ix_entitlements_id",
    ):
        op.drop_index(name, table_name="entitlements")
    op.drop_constraint("uq_entitlement_source", "entitlements", type_="unique")
    op.drop_table("entitlements")
