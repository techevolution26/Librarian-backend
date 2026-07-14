from app.models.book import Book
from app.models.library_item import LibraryItem
from app.routes.library import merge_pdf_progress_state, to_library_item_read
from app.schemas.library import PdfProgressUpdate


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


def test_merge_pdf_progress_state_keeps_existing_page_when_previous_page_clicked():
    item = LibraryItem(
        id=11,
        user_id=1,
        book_id=2,
        status="reading",
        progress=40,
        current_page=3,
        total_pages=10,
        bookmark_page=2,
    )

    payload = PdfProgressUpdate(current_page=2, total_pages=10, progress=40, bookmark_page=2)

    merged = merge_pdf_progress_state(item, payload)

    assert merged.current_page == 3
    assert merged.progress == 40
    assert merged.total_pages == 10
    assert merged.bookmark_page == 2
