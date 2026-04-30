from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    theme: Mapped[str] = mapped_column(String(20), default="dark")
    density: Mapped[str] = mapped_column(String(20), default="comfortable")
    reading_mode: Mapped[str] = mapped_column(String(20), default="scroll")
    font_size: Mapped[str] = mapped_column(String(20), default="medium")
    line_height: Mapped[str] = mapped_column(String(20), default="comfortable")
    auto_bookmark: Mapped[bool] = mapped_column(Boolean, default=True)
    show_progress_bar: Mapped[bool] = mapped_column(Boolean, default=True)
    email_updates: Mapped[bool] = mapped_column(Boolean, default=True)
    reading_reminders: Mapped[bool] = mapped_column(Boolean, default=True)
    product_announcements: Mapped[bool] = mapped_column(Boolean, default=False)
    profile_visibility: Mapped[str] = mapped_column(String(20), default="private")
    share_reading_activity: Mapped[bool] = mapped_column(Boolean, default=False)
    user: Mapped["User"] = relationship(back_populates="settings")
    preferred_genres: Mapped[list[str]] = mapped_column(JSON, default=list)
    reading_goals: Mapped[list[str]] = mapped_column(JSON, default=list)
    content_styles: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferred_lengths: Mapped[list[str]] = mapped_column(JSON, default=list)
    weekly_target: Mapped[str | None] = mapped_column(String(80), nullable=True)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)