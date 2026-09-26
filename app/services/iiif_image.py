from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError


IIIF_CONTEXT = "http://iiif.io/api/image/3/context.json"
IIIF_PROTOCOL = "http://iiif.io/api/image"
SUPPORTED_FORMATS = {"jpg", "png", "webp"}
SUPPORTED_QUALITIES = {"default", "color", "gray"}


@dataclass(frozen=True)
class IIIFImageRequest:
    region: str
    size: str
    rotation: str
    quality: str
    format: str


@dataclass(frozen=True)
class IIIFImageInfo:
    width: int
    height: int


def _positive_int(value: str, label: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be an integer") from exc
    if parsed <= 0:
        raise ValueError(f"{label} must be greater than zero")
    return parsed


def _non_negative_float(value: str, label: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be a number") from exc
    if parsed < 0:
        raise ValueError(f"{label} must not be negative")
    return parsed


def parse_request(region: str, size: str, rotation: str, quality: str, format: str) -> IIIFImageRequest:
    normalized_format = format.lower()
    if normalized_format not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported IIIF format: {format}")
    normalized_quality = quality.lower()
    if normalized_quality not in SUPPORTED_QUALITIES:
        raise ValueError(f"Unsupported IIIF quality: {quality}")
    if rotation.startswith("!"):
        raise ValueError("Mirroring is not supported")
    try:
        angle = float(rotation)
    except ValueError as exc:
        raise ValueError("Rotation must be a numeric angle") from exc
    if angle < 0 or angle >= 360:
        raise ValueError("Rotation must be between 0 and 359.999 degrees")
    if angle % 90 != 0:
        raise ValueError("Only 90-degree rotation increments are supported")
    if region != "full" and region != "square":
        parts = region.split(",")
        if len(parts) != 4:
            raise ValueError("Region must be full, square, x,y,w,h, or pct:x,y,w,h")
        if region.startswith("pct:"):
            values = region[4:].split(",")
            if len(values) != 4:
                raise ValueError("Percentage region must contain four values")
            for value in values:
                parsed = _non_negative_float(value, "Region percentage")
                if parsed > 100:
                    raise ValueError("Region percentage must not exceed 100")
        else:
            for value in parts:
                _non_negative_float(value, "Region coordinate")
    if size != "max" and not size.startswith("pct:"):
        normalized_size = size[1:] if size.startswith("!") else size
        if normalized_size.startswith("^"):
            raise ValueError("Upscaling is not supported")
        if normalized_size not in {"max", ""}:
            parts = normalized_size.split(",")
            if len(parts) != 2:
                raise ValueError("Size must be max, pct:n, w,, ,h, w,h, or !w,h")
            for value in parts:
                if value:
                    _positive_int(value, "Size")
    if size.startswith("pct:"):
        _non_negative_float(size[4:], "Size percentage")
        if float(size[4:]) <= 0:
            raise ValueError("Size percentage must be greater than zero")
    return IIIFImageRequest(region, size, rotation, normalized_quality, normalized_format)


def inspect_image(path: Path) -> IIIFImageInfo:
    try:
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source)
            return IIIFImageInfo(width=image.width, height=image.height)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
        raise ValueError("Stored asset is not a readable image") from exc


def _region_box(image: Image.Image, region: str) -> tuple[int, int, int, int]:
    width, height = image.size
    if region == "full":
        return 0, 0, width, height
    if region == "square":
        side = min(width, height)
        return (width - side) // 2, (height - side) // 2, (width + side) // 2, (height + side) // 2
    if region.startswith("pct:"):
        values = [float(value) for value in region[4:].split(",")]
        x, y, w, h = [value / 100 for value in values]
        return (
            int(round(width * x)),
            int(round(height * y)),
            int(round(width * (x + w))),
            int(round(height * (y + h))),
        )
    x, y, w, h = [float(value) for value in region.split(",")]
    return int(x), int(y), int(x + w), int(y + h)


def _clamp_box(box: tuple[int, int, int, int], width: int, height: int) -> tuple[int, int, int, int]:
    left, top, right, bottom = box
    left = max(0, min(left, width - 1))
    top = max(0, min(top, height - 1))
    right = max(left + 1, min(right, width))
    bottom = max(top + 1, min(bottom, height))
    return left, top, right, bottom


def _target_size(size: str, width: int, height: int) -> tuple[int, int]:
    if size == "max":
        return width, height
    if size.startswith("pct:"):
        scale = float(size[4:]) / 100
        return max(1, round(width * scale)), max(1, round(height * scale))

    confined = size.startswith("!")
    value = size[1:] if confined else size
    if value.startswith("^"):
        value = value[1:]
        confined = False
    if value.endswith(","):
        target_width = _positive_int(value[:-1], "Size width")
        scale = target_width / width
        return target_width, max(1, round(height * scale))
    if value.startswith(","):
        target_height = _positive_int(value[1:], "Size height")
        scale = target_height / height
        return max(1, round(width * scale)), target_height

    dimensions = value.split(",")
    if len(dimensions) != 2:
        raise ValueError("Size must contain width and height")
    target_width = _positive_int(dimensions[0], "Size width")
    target_height = _positive_int(dimensions[1], "Size height")
    if confined:
        scale = min(target_width / width, target_height / height)
        return max(1, round(width * scale)), max(1, round(height * scale))
    return target_width, target_height


def _rotate(image: Image.Image, rotation: str) -> Image.Image:
    angle = int(float(rotation))
    if angle == 0:
        return image
    return image.rotate(angle, expand=True)


def render_image(path: Path, request: IIIFImageRequest) -> tuple[bytes, str]:
    try:
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).copy()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
        raise ValueError("Stored asset is not a readable image") from exc

    box = _clamp_box(_region_box(image, request.region), image.width, image.height)
    image = image.crop(box)
    target_width, target_height = _target_size(request.size, image.width, image.height)
    if target_width > image.width or target_height > image.height:
        raise ValueError("Upscaling is not supported")
    if (target_width, target_height) != image.size:
        image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
    image = _rotate(image, request.rotation)

    if request.quality == "gray":
        image = ImageOps.grayscale(image)
    elif request.quality == "color" and image.mode not in {"RGB", "RGBA"}:
        image = image.convert("RGBA" if "transparency" in image.info else "RGB")

    output_format = "JPEG" if request.format in {"jpg", "jpeg"} else request.format.upper()
    if output_format == "JPEG":
        if image.mode not in {"RGB", "L"}:
            background = Image.new("RGB", image.size, "white")
            if "A" in image.getbands():
                background.paste(image, mask=image.getchannel("A"))
            else:
                background.paste(image)
            image = background
        media_type = "image/jpeg"
        save_kwargs = {"quality": 90, "optimize": True}
    elif output_format == "PNG":
        media_type = "image/png"
        save_kwargs = {"optimize": True}
    else:
        media_type = "image/webp"
        save_kwargs = {"quality": 90, "method": 6}

    output = BytesIO()
    image.save(output, format=output_format, **save_kwargs)
    return output.getvalue(), media_type


def info_document(
    identifier: str,
    service_id: str,
    width: int,
    height: int,
    *,
    rights: str | None = None,
) -> dict[str, object]:
    document: dict[str, object] = {
        "@context": IIIF_CONTEXT,
        "id": service_id,
        "type": "ImageService3",
        "protocol": IIIF_PROTOCOL,
        "profile": "level1",
        "width": width,
        "height": height,
        "extraQualities": ["color", "gray"],
        "extraFormats": ["webp"],
        "extraFeatures": [
            "cors",
            "regionByPct",
            "regionSquare",
            "rotationBy90s",
            "sizeByConfinedWh",
            "sizeByH",
            "sizeByPct",
            "sizeByW",
            "sizeByWh",
        ],
        "preferredFormats": ["jpg", "png", "webp"],
    }
    if rights and (rights.startswith("http://") or rights.startswith("https://")):
        document["rights"] = rights
    return document
