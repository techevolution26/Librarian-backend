from pathlib import Path

from PIL import Image

from app.services.iiif_image import (
    IIIFImageInfo,
    info_document,
    inspect_image,
    parse_request,
    render_image,
)


def test_parse_supported_request() -> None:
    request = parse_request("pct:10,10,80,80", "!400,400", "90", "gray", "jpg")
    assert request.quality == "gray"
    assert request.format == "jpg"


def test_parse_rejects_unsupported_upscaling() -> None:
    try:
        parse_request("full", "^1000,1000", "0", "default", "jpg")
    except ValueError as exc:
        assert "Upscaling" in str(exc)
    else:
        raise AssertionError("Expected upscaling to be rejected")


def test_render_region_size_rotation_and_gray(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (800, 400), "white").save(source)

    request = parse_request("square", "200,200", "90", "gray", "png")
    body, media_type = render_image(source, request)

    assert media_type == "image/png"
    output = tmp_path / "output.png"
    output.write_bytes(body)
    with Image.open(output) as image:
        assert image.size == (200, 200)
        assert image.mode == "L"


def test_inspect_image_reports_dimensions(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (640, 480), "white").save(source)
    info = inspect_image(source)
    assert info == IIIFImageInfo(width=640, height=480)


def test_info_document_is_iiif_image_service() -> None:
    document = info_document(
        "tl:canvas:abc",
        "https://example.test/iiif/3/tl:canvas:abc",
        640,
        480,
        rights="https://rightsstatements.org/vocab/InC/1.0/",
    )
    assert document["type"] == "ImageService3"
    assert document["profile"] == "level1"
    assert document["width"] == 640
    assert document["height"] == 480
    assert document["rights"].startswith("https://")
