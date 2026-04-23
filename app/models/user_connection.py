from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserConnection(Base):
    __tablename__ = "user_connections"
    __table_args__ = (
        UniqueConstraint("requester_id", "addressee_id", name="uq_user_connection_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    requester_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    addressee_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        index=True,
    )  # pending | accepted | declined | blocked

    relationship_type: Mapped[str] = mapped_column(
        String(20),
        default="friend",
    )  # friend | family | school | mentor | other

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    requester: Mapped["User"] = relationship(
        "User",
        foreign_keys=[requester_id],
    )
    addressee: Mapped["User"] = relationship(
        "User",
        foreign_keys=[addressee_id],
    )