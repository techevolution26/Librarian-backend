from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.circle_book import CircleBook
    from app.models.circle_member import CircleMember
    from app.models.circle_progress_update import CircleProgressUpdate
    from app.models.user import User


class Circle(Base):
    __tablename__ = "circles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    visibility: Mapped[str] = mapped_column(String(20), default="private")
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id])

    members: Mapped[list["CircleMember"]] = relationship(
        back_populates="circle",
        cascade="all, delete-orphan",
    )
    books: Mapped[list["CircleBook"]] = relationship(
        back_populates="circle",
        cascade="all, delete-orphan",
    )
    progress_updates: Mapped[list["CircleProgressUpdate"]] = relationship(
        back_populates="circle",
        cascade="all, delete-orphan",
    )