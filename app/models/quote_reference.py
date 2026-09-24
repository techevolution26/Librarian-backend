from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class QuoteReference(Base):
    """A private, durable reference from a reader to an archival source.

    The Book remains the authoritative source for bibliographic identity. This
    record stores the user's captured passage and locator so the reference can
    survive edits to a personal note or deletion of the originating highlight.
    """

    __tablename__ = "quote_references"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    highlight_id: Mapped[int | None] = mapped_column(
        ForeignKey("highlights.id", ondelete="SET NULL"), nullable=True, index=True
    )
    note_id: Mapped[int | None] = mapped_column(
        ForeignKey("notes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    locator: Mapped[str | None] = mapped_column(Text, nullable=True)
    quote_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User")
    book = relationship("Book")
    highlight = relationship("Highlight")
    note = relationship("Note")
