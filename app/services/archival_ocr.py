from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.services.storage import get_storage_backend

TESSERACT_BINARY = "tesseract"
OCR_TIMEOUT_SECONDS = 120


def resolve_image(storage_key: str) -> Path:
    backend = get_storage_backend()
    path = backend.resolve(storage_key)
    if not path.is_file():
        raise FileNotFoundError(f"Stored image does not exist: {storage_key}")
    return path


def tesseract_version() -> str:
    binary = shutil.which(TESSERACT_BINARY)
    if not binary:
        raise RuntimeError("Tesseract OCR is not installed on this deployment")
    result = subprocess.run(
        [binary, "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    first_line = result.stdout.splitlines()[0] if result.stdout else ""
    if result.returncode != 0 or not first_line.startswith("tesseract "):
        raise RuntimeError("Tesseract OCR could not report its version")
    return first_line.removeprefix("tesseract ").strip()


def extract_text(path: Path, language: str) -> tuple[str, str]:
    binary = shutil.which(TESSERACT_BINARY)
    if not binary:
        raise RuntimeError("Tesseract OCR is not installed on this deployment")

    version = tesseract_version()
    result = subprocess.run(
        [binary, str(path), "stdout", "--dpi", "300", "-l", language],
        check=False,
        capture_output=True,
        text=True,
        timeout=OCR_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        detail = (result.stderr or "OCR engine failed").strip()
        raise RuntimeError(detail[-1000:])

    text = result.stdout.strip()
    if not text:
        raise ValueError("OCR produced no text for this canvas")
    return text, version
