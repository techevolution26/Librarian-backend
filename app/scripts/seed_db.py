from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app.models import Book, LibraryItem, User, UserSettings


BOOK_SEED = [
    {
        "title": "Atomic Habits",
        "author": "James Clear",
        "cover": "/atomichabits.jpg",
        "description": "Tiny changes, remarkable results.",
        "rating": 4.8,
        "pages": 320,
        "genre": ["Productivity", "Mindset"],
        "source_type": "text",
        "content_text": "Chapter 1\n\nSmall habits compound over time...\n\nChapter 2\n\nIdentity-based habits...",
        "mime_type": "text/plain",
        "source_url": None,
        "source_path": None,
    },
    {
        "title": "Deep Work",
        "author": "Cal Newport",
        "cover": "/deepwork.jpg",
        "description": "Rules for focused success in a distracted world.",
        "rating": 4.7,
        "pages": 304,
        "genre": ["Productivity"],
        "source_type": "text",
        "content_text": "Chapter 1\n\nDeep work is valuable...\n\nChapter 2\n\nThe ability to focus is rare...",
        "mime_type": "text/plain",
        "source_url": None,
        "source_path": None,
    },
    {
        "title": "The Innovator's Dilemma",
        "author": "Clayton M. Christensen",
        "cover": "/theinnovatorsdilemma.jpg",
        "description": "A book about disruptive innovation and how companies can avoid it.",
        "rating": 4.6,
        "pages": 288,
        "genre": ["Business"],
    },
    {
        "title": "The 4-Hour Workweek",
        "author": "Tim Ferriss",
        "cover": "/the4hourworkweek.jpg",
        "description": "A guide to lifestyle design and productivity.",
        "rating": 4.6,
        "pages": 320,
        "genre": ["Mindset"],
    },
]


def reset_schema() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def seed() -> None:
    with SessionLocal() as db:
        db: Session

        user = User(
            full_name="Tech Resolute",
            email="techresolute@example.com",
            plan="free",
            avatar_url=None,
        )
        db.add(user)
        db.flush()

        settings = UserSettings(
            user_id=user.id,
            theme="dark",
            density="comfortable",
            reading_mode="scroll",
            font_size="medium",
            line_height="comfortable",
            auto_bookmark=True,
            show_progress_bar=True,
            email_updates=True,
            reading_reminders=True,
            product_announcements=False,
            profile_visibility="private",
            share_reading_activity=False,
        )
        db.add(settings)

        books: list[Book] = []
        for item in BOOK_SEED:
            book = Book(
                title=item["title"],
                author=item["author"],
                cover=item["cover"],
                description=item["description"],
                rating=item["rating"],
                pages=item["pages"],
                source_type=item.get("source_type"),
                content_text=item.get("content_text"),
                mime_type=item.get("mime_type"),
                source_url=item.get("source_url"),
                source_path=item.get("source_path"),
            )
            book.genres = item["genre"]
            db.add(book)
            books.append(book)

        db.flush()

        library_items = [
            LibraryItem(
                user_id=user.id,
                book_id=books[0].id,
                status="reading",
                progress=78,
            ),
            LibraryItem(
                user_id=user.id,
                book_id=books[1].id,
                status="reading",
                progress=42,
            ),
            LibraryItem(
                user_id=user.id,
                book_id=books[2].id,
                status="saved",
                progress=0,
            ),
            LibraryItem(
                user_id=user.id,
                book_id=books[3].id,
                status="finished",
                progress=100,
                finished_at=datetime.now(timezone.utc),
            ),
        ]
        db.add_all(library_items)
        db.commit()

        result = db.execute(text("SELECT COUNT(*) AS count FROM books"))
        books_count = result.scalar_one()

        print(" Database connection confirmed")
        print(f" Seed complete: {books_count} books inserted")
        print(f" User inserted: {user.email}")


if __name__ == "__main__":
    reset_schema()
    seed()