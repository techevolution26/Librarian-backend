from alembic import op
import sqlalchemy as sa

revision = "0f801e29e3ae"
down_revision = "779e253b8e8b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_settings", sa.Column("preferred_genres", sa.JSON(), nullable=True))
    op.add_column("user_settings", sa.Column("reading_goals", sa.JSON(), nullable=True))
    op.add_column("user_settings", sa.Column("content_styles", sa.JSON(), nullable=True))
    op.add_column("user_settings", sa.Column("preferred_lengths", sa.JSON(), nullable=True))
    op.add_column("user_settings", sa.Column("weekly_target", sa.String(length=80), nullable=True))
    op.add_column(
        "user_settings",
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "onboarding_completed")
    op.drop_column("user_settings", "weekly_target")
    op.drop_column("user_settings", "preferred_lengths")
    op.drop_column("user_settings", "content_styles")
    op.drop_column("user_settings", "reading_goals")
    op.drop_column("user_settings", "preferred_genres")