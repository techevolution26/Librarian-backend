from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    notebook_id: Mapped[int] = mapped_column(ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False, index=True)
    book_id: Mapped[int | None] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=True, index=True)
    bookmark_id: Mapped[int | None] = mapped_column(ForeignKey("bookmarks.id", ondelete="SET NULL"), nullable=True, index=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False, default="Untitled note")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    notebook = relationship("Notebook", back_populates="notes")
    book = relationship("Book")
    bookmark = relationship("Bookmark")
