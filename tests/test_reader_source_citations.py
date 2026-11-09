from datetime import datetime, timezone
from types import SimpleNamespace

from app.routes.quote_references import format_source_anchor_location, to_read


def _row(**overrides):
    values = {
        "id": 1,
        "user_id": 7,
        "book_id": 12,
        "highlight_id": 4,
        "note_id": None,
        "source_anchor_id": 20,
        "page_number": None,
        "locator": None,
        "quote_text": "Selected archival passage",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _book():
    return SimpleNamespace(title="Letters from the Coast", author="Archive Collection")


def _anchor(locator_type: str, locator_data: dict, **overrides):
    values = {
        "id": 20,
        "locator_type": locator_type,
        "locator_data": locator_data,
        "source_canvas_identifier": locator_data.get("canvas_identifier"),
        "source_accession_number": "ACC-0012",
        "source_persistent_identifier": "AO:KLF:12",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_canvas_quote_citation_uses_archival_identity_and_canvas_label():
    anchor = _anchor("iiif_canvas", {"type": "iiif_canvas", "canvas_identifier": "tl:canvas:12"})

    result = to_read(_row(), _book(), anchor, "Folio 1r")

    assert "Canvas “Folio 1r” [tl:canvas:12]" in result.citation
    assert "Accession ACC-0012" in result.citation
    assert "Archival ID AO:KLF:12" in result.citation


def test_image_region_citation_preserves_region_coordinates():
    anchor = _anchor(
        "image_region",
        {
            "type": "image_region",
            "canvas_identifier": "tl:canvas:13",
            "x": 12.5,
            "y": 8.0,
            "width": 24.5,
            "height": 16.0,
            "coordinate_space": "percent",
        },
    )

    locator = format_source_anchor_location(anchor, canvas_label="Map detail")

    assert locator == "Canvas “Map detail” [tl:canvas:13], region x=12.5%, y=8%, w=24.5%, h=16%"


def test_ocr_and_plain_text_citations_use_one_based_character_ranges():
    ocr = _anchor(
        "ocr_span",
        {"type": "ocr_span", "canvas_identifier": "tl:canvas:14", "start_offset": 0, "end_offset": 9},
    )
    text = _anchor("text_span", {"type": "text_span", "start_offset": 18, "end_offset": 29})

    assert format_source_anchor_location(ocr, canvas_label="Folio 2v") == (
        "Canvas “Folio 2v” [tl:canvas:14], OCR characters 1–9"
    )
    assert format_source_anchor_location(text) == "text characters 19–29"


def test_pdf_and_legacy_page_citations_keep_page_semantics():
    anchor = _anchor("pdf_text", {"type": "pdf_text", "page_number": 3, "start_offset": 12, "end_offset": 20})

    anchored = to_read(_row(page_number=3), _book(), anchor)
    legacy = to_read(_row(source_anchor_id=None, page_number=5), _book())

    assert "p. 3, text characters 13–20" in anchored.citation
    assert "p. 5" in legacy.citation
