from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.circle import Circle
    from app.models.circle_progress_update import CircleProgressUpdate
    from app.models.user import User


class CircleBook(Base):
    __tablename__ = "circle_books"
    __table_args__ = (
        UniqueConstraint("circle_id", "book_id", name="uq_circle_book_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    circle_id: Mapped[int] = mapped_column(
        ForeignKey("circles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    title_override: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    circle: Mapped["Circle"] = relationship(back_populates="books")
    book: Mapped["Book"] = relationship("Book")
    created_by_user: Mapped["User"] = relationship("User", foreign_keys=[created_by_user_id])

    progress_updates: Mapped[list["CircleProgressUpdate"]] = relationship(
        back_populates="circle_book",
        cascade="all, delete-orphan",
    )