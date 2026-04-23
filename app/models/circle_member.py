from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.circle import Circle
    from app.models.user import User


class CircleMember(Base):
    __tablename__ = "circle_members"
    __table_args__ = (
        UniqueConstraint("circle_id", "user_id", name="uq_circle_member_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    circle_id: Mapped[int] = mapped_column(
        ForeignKey("circles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(String(20), default="member")
    status: Mapped[str] = mapped_column(String(20), default="active")

    invited_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    joined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    circle: Mapped["Circle"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    invited_by_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[invited_by_user_id],
    )