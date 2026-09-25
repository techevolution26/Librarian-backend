from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.circle import Circle
    from app.models.user import User


class CircleJoinRequest(Base):
    __tablename__ = "circle_join_requests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    circle_id: Mapped[int] = mapped_column(ForeignKey("circles.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    reviewed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    circle: Mapped["Circle"] = relationship("Circle")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
