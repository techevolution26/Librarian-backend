from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


CREATOR_ACCOUNT_STATUSES = {"active", "suspended"}


class CreatorAccount(Base):
    __tablename__ = "creator_accounts"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_creator_accounts_user_id"),
        UniqueConstraint("slug", name="uq_creator_accounts_slug"),
        Index("ix_creator_accounts_status", "status"),
        Index("ix_creator_accounts_public", "is_public"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    profile_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", back_populates="creator_account")
    book_submissions = relationship(
        "CreatorBookSubmission",
        back_populates="creator_account",
        cascade="all, delete-orphan",
        order_by="CreatorBookSubmission.created_at.desc()",
    )
