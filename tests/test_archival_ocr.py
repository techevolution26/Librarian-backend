from pathlib import Path

from app.models.archival_ocr import OCR_STATUSES
from app.services.archival_ocr import extract_text


def test_ocr_statuses_are_explicit() -> None:
    assert OCR_STATUSES == {"verified", "stale", "failed"}


def test_ocr_engine_extracts_text_from_image(tmp_path: Path) -> None:
    from PIL import Image, ImageDraw

    image_path = tmp_path / "ocr.png"
    image = Image.new("RGB", (900, 180), "white")
    draw = ImageDraw.Draw(image)
    draw.text((40, 60), "THE LIBRARIAN OCR TEST", fill="black")
    image.save(image_path)

    text, version = extract_text(image_path, "eng")

    assert "LIBRARIAN" in text.upper()
    assert version


def test_ocr_records_are_derived_not_archival_metadata() -> None:
    from app.models.archival_ocr import ArchivalOCRPage

    assert ArchivalOCRPage.__tablename__ == "archival_ocr_pages"
    assert "text" in ArchivalOCRPage.__table__.columns
    assert "source_checksum_sha256" in ArchivalOCRPage.__table__.columns
