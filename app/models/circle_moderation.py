from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.circle import Circle
    from app.models.user import User


class CircleModerationReport(Base):
    __tablename__ = "circle_moderation_reports"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    circle_id: Mapped[int] = mapped_column(ForeignKey("circles.id", ondelete="CASCADE"), nullable=False, index=True)
    reporter_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)
    reviewed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    action: Mapped[str | None] = mapped_column(String(30), nullable=True)
    action_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    circle: Mapped["Circle"] = relationship("Circle")
    reporter: Mapped["User"] = relationship("User", foreign_keys=[reporter_user_id])
    reviewer: Mapped["User | None"] = relationship("User", foreign_keys=[reviewed_by_user_id])
