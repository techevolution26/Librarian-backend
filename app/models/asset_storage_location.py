from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


STORAGE_PROVIDERS = {"local", "object_storage"}
STORAGE_LOCATION_STATUSES = {"active", "unavailable", "retired"}


class AssetStorageLocation(Base):
    """Physical storage location for a logical BookAsset.

    BookAsset identifies the logical/versioned asset. This model identifies
    where a physical copy of that asset currently lives. Keeping the two
    identities separate allows local storage to remain the working backend
    while durable object storage and replication are introduced later.
    """

    __tablename__ = "asset_storage_locations"
    __table_args__ = (
        UniqueConstraint("asset_id", "provider", "bucket", "storage_key", name="uq_asset_storage_location"),
        Index("ix_asset_storage_locations_asset_id", "asset_id"),
        Index("ix_asset_storage_locations_provider", "provider"),
        Index("ix_asset_storage_locations_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("book_assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(30), nullable=False, default="local")
    bucket: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    public_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    asset = relationship("BookAsset", back_populates="storage_locations")
