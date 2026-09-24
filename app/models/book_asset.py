from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

ASSET_ROLES = {"preservation_master", "access"}


class BookAsset(Base):
    __tablename__ = "book_assets"
    __table_args__ = (
        UniqueConstraint(
            "book_id",
            "asset_type",
            "asset_role",
            "version",
            name="uq_book_asset_version",
        ),
        CheckConstraint(
            "asset_role IN ('preservation_master', 'access')", name="ck_book_asset_role"
        ),
        Index(
            "uq_book_asset_current",
            "book_id",
            "asset_type",
            "asset_role",
            unique=True,
            postgresql_where=text("is_current = true"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    asset_role: Mapped[str] = mapped_column(
        String(30), nullable=False, default="access", index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    public_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    book = relationship("Book", back_populates="assets")
    uploader = relationship("User")
