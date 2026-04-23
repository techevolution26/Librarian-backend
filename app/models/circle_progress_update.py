from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.circle import Circle
    from app.models.circle_book import CircleBook
    from app.models.library_item import LibraryItem
    from app.models.user import User


class CircleProgressUpdate(Base):
    __tablename__ = "circle_progress_updates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    circle_id: Mapped[int] = mapped_column(
        ForeignKey("circles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    circle_book_id: Mapped[int | None] = mapped_column(
        ForeignKey("circle_books.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    library_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("library_items.id", ondelete="SET NULL"),
        nullable=True,
    )

    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    current_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bookmark_page: Mapped[int | None] = mapped_column(Integer, nullable=True)

    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    visibility: Mapped[str] = mapped_column(String(20), default="circle")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    circle: Mapped["Circle"] = relationship(back_populates="progress_updates")
    circle_book: Mapped["CircleBook | None"] = relationship(back_populates="progress_updates")
    user: Mapped["User"] = relationship("User")
    library_item: Mapped["LibraryItem | None"] = relationship("LibraryItem")