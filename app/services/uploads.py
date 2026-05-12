from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, Request, UploadFile

from app.core.config import get_settings


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
    if file.content_type not in allowed_content_types:
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


async def save_upload_file(
    file: UploadFile,
    destination_dir: Path,
    fallback_filename: str,
    max_size_mb: int,
    label: str,
) -> tuple[str, Path]:
    destination_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or fallback_filename).suffix or Path(
        fallback_filename
    ).suffix

    filename = f"{uuid4().hex}{suffix}"
    destination = destination_dir / filename

    max_size_bytes = max_size_mb * 1024 * 1024
    total_size = 0

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