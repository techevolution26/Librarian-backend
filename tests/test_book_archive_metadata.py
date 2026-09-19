from pathlib import Path

from app.models.book import Book, ORIGINAL_FORMATS, RIGHTS_STATEMENTS
from app.services.uploads import compute_sha256, generate_accession_no


def test_book_subjects_roundtrip():
    book = Book(
        id=1,
        title="Sample",
        author="Author",
        cover="cover.jpg",
        description="desc",
    )

    book.subjects = ["Oral History", "  Folklore ", ""]

    assert book.subjects == ["Oral History", "Folklore"]
    assert book.subjects_csv == "Oral History,Folklore"


def test_book_column_defaults_are_archive_safe():
    # SQLAlchemy column defaults apply at flush time, not on plain construction,
    # so assert against the column definitions rather than a bare Book() instance.
    columns = Book.__table__.columns

    assert columns["language"].default.arg == "en"
    assert columns["original_format"].default.arg == "born-digital"
    assert columns["rights_statement"].default.arg == "all-rights-reserved"


def test_is_archival_format_false_for_born_digital():
    book = Book(
        id=2,
        title="Sample",
        author="Author",
        cover="cover.jpg",
        description="desc",
        original_format="born-digital",
    )

    assert book.is_archival_format is False


def test_is_archival_format_true_for_non_digital_origin():
    book = Book(
        id=3,
        title="Sample",
        author="Author",
        cover="cover.jpg",
        description="desc",
        original_format="manuscript",
    )

    assert book.is_archival_format is True


def test_original_format_and_rights_vocabulary_are_stable():
    # Guards against accidentally renaming a value that the frontend/mobile
    # filter chips and validation both depend on.
    assert ORIGINAL_FORMATS == {"born-digital", "printed", "manuscript", "oral-transcription"}
    assert RIGHTS_STATEMENTS == {"public-domain", "cc-by", "all-rights-reserved", "restricted"}


def test_generate_accession_no_is_prefixed_and_unique():
    first = generate_accession_no()
    second = generate_accession_no()

    assert first.startswith("TL-")
    assert first != second


def test_compute_sha256_matches_known_hash(tmp_path: Path):
    file_path = tmp_path / "sample.txt"
    file_path.write_bytes(b"hello librarian")

    import hashlib

    expected = hashlib.sha256(b"hello librarian").hexdigest()

    assert compute_sha256(file_path) == expected
