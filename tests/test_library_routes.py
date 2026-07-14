from app.models.book import Book
from app.models.library_item import LibraryItem
from app.routes.library import to_library_item_read


def test_to_library_item_read_includes_book_content_type():
    book = Book(
        id=1,
        title="Example Book",
        author="Test Author",
        cover="cover.jpg",
        description="A sample book",
        rating=4.5,
        pages=120,
        genre_csv="fiction",
        source_type="application/pdf",
        source_url="https://example.com/book.pdf",
        mime_type="application/pdf",
    )

    item = LibraryItem(
        id=10,
        user_id=1,
        book_id=book.id,
        status="reading",
        progress=25,
        book=book,
    )

    result = to_library_item_read(item)

    assert result.book.content_type == "application/pdf"
    assert result.book.source_type == "application/pdf"
