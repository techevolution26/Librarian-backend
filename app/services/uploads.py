import hashlib
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, Request, UploadFile

from app.core.config import get_settings


def compute_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Hash a stored file so its integrity can be verified later — the same
    "insurance against loss/corruption" idea behind archival checksums."""
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)

    return digest.hexdigest()


def generate_accession_no(prefix: str = "TL") -> str:
    """A stable catalog/accession number, independent of the row's future
    autoincrement id, in the spirit of an archive's catalog number."""
    return f"{prefix}-{uuid4().hex[:8].upper()}"


def build_public_static_url(path: str, request: Request) -> str:
    settings = get_settings()

    if settings.public_backend_url:
        return f"{settings.public_backend_url.rstrip('/')}/{path.lstrip('/')}"

    return f"{str(request.base_url).rstrip('/')}/{path.lstrip('/')}"


def validate_upload_file(
    file: UploadFile,
    allowed_content_types: set[str],
    max_size_mb: int,
    label: str,
) -> None:
    content_type = (file.content_type or "").lower().strip()
    generic_types = {"", "application/octet-stream", "binary/octet-stream"}

    # Native mobile multipart implementations may omit the MIME type or send
    # application/octet-stream. The content signature is validated separately
    # by save_upload_file, so MIME remains advisory here.
    if content_type not in allowed_content_types and content_type not in generic_types:
        raise HTTPException(
            status_code=400,
            detail=f"{label} file type is not supported",
        )

    max_size_bytes = max_size_mb * 1024 * 1024

    if file.size is not None and file.size > max_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"{label} file is too large. Maximum allowed size is {max_size_mb}MB.",
        )




def canonical_content_type(label: str, suffix: str) -> str:
    if label == "PDF":
        return "application/pdf"
    if label in {"Cover", "Avatar"}:
        return {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }.get(suffix, "application/octet-stream")
    return "application/octet-stream"

async def save_upload_file(
    file: UploadFile,
    destination_dir: Path,
    fallback_filename: str,
    max_size_mb: int,
    label: str,
) -> tuple[str, Path]:
    destination_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or fallback_filename).suffix.lower()
    allowed_suffixes = {
        "PDF": {".pdf"},
        "Cover": {".png", ".jpg", ".jpeg", ".webp"},
        "Avatar": {".png", ".jpg", ".jpeg", ".webp"},
    }.get(label, {Path(fallback_filename).suffix.lower()})

    if suffix not in allowed_suffixes:
        suffix = Path(fallback_filename).suffix.lower()

    filename = f"{uuid4().hex}{suffix}"
    destination = destination_dir / filename

    max_size_bytes = max_size_mb * 1024 * 1024
    total_size = 0

    signature = await file.read(16)
    await file.seek(0)

    if label == "PDF" and not signature.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="PDF content signature is invalid")

    if label in {"Cover", "Avatar"}:
        valid_image = (
            signature.startswith(b"\x89PNG\r\n\x1a\n")
            or signature.startswith(b"\xff\xd8\xff")
            or (signature.startswith(b"RIFF") and signature[8:12] == b"WEBP")
        )
        if not valid_image:
            raise HTTPException(status_code=400, detail=f"{label} image content signature is invalid")

    with destination.open("wb") as output:
        while True:
            chunk = await file.read(1024 * 1024)

            if not chunk:
                break

            total_size += len(chunk)

            if total_size > max_size_bytes:
                output.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"{label} file is too large. Maximum allowed size is {max_size_mb}MB.",
                )

            output.write(chunk)

    return filename, destination