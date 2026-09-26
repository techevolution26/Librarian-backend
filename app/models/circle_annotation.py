from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.circle import Circle
    from app.models.circle_book import CircleBook
    from app.models.user import User


class CircleAnnotation(Base):
    """A community interpretation anchored to a Circle's shared book/page.

    This is deliberately separate from private Reader highlights and notes and
    has no relationship that can mutate archival metadata.
    """

    __tablename__ = "circle_annotations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    circle_id: Mapped[int] = mapped_column(
        ForeignKey("circles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    circle_book_id: Mapped[int] = mapped_column(
        ForeignKey("circle_books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String(20), nullable=False, default="circle")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    circle: Mapped["Circle"] = relationship("Circle")
    circle_book: Mapped["CircleBook"] = relationship("CircleBook")
    book: Mapped["Book"] = relationship("Book")
    user: Mapped["User"] = relationship("User")
