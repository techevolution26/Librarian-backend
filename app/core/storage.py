from __future__ import annotations

import os
from pathlib import Path


def get_storage_root() -> Path:
    # Local default: ./storage
    # Railway override: /app/storage
    raw = os.getenv("STORAGE_DIR", "storage")
    return Path(raw).expanduser().resolve()


STORAGE_ROOT = get_storage_root()
BOOKS_STORAGE_DIR = STORAGE_ROOT / "books"
AVATARS_STORAGE_DIR = STORAGE_ROOT / "avatars"


def ensure_storage_dirs() -> None:
    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    BOOKS_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    AVATARS_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def build_public_file_url(base_url: str, folder: str, filename: str) -> str:
    public_base = os.getenv("PUBLIC_BASE_URL", base_url.rstrip("/"))
    return f"{public_base}/static/{folder}/{filename}"