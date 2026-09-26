from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.circle import Circle
    from app.models.circle_book import CircleBook
    from app.models.user import User


class CircleDiscussion(Base):
    __tablename__ = "circle_discussions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    circle_id: Mapped[int] = mapped_column(ForeignKey("circles.id", ondelete="CASCADE"), nullable=False, index=True)
    circle_book_id: Mapped[int] = mapped_column(ForeignKey("circle_books.id", ondelete="CASCADE"), nullable=False, index=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    circle: Mapped["Circle"] = relationship("Circle")
    circle_book: Mapped["CircleBook"] = relationship("CircleBook")
    user: Mapped["User"] = relationship("User")
    replies: Mapped[list["CircleDiscussionReply"]] = relationship(
        "CircleDiscussionReply",
        back_populates="discussion",
        cascade="all, delete-orphan",
        order_by="CircleDiscussionReply.created_at.asc()",
    )


class CircleDiscussionReply(Base):
    __tablename__ = "circle_discussion_replies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    discussion_id: Mapped[int] = mapped_column(ForeignKey("circle_discussions.id", ondelete="CASCADE"), nullable=False, index=True)
    circle_id: Mapped[int] = mapped_column(ForeignKey("circles.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    discussion: Mapped["CircleDiscussion"] = relationship("CircleDiscussion", back_populates="replies")
    circle: Mapped["Circle"] = relationship("Circle")
    user: Mapped["User"] = relationship("User")
