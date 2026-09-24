from __future__ import annotations

from pathlib import Path

from app.core.storage import get_storage_root
from app.services.uploads import compute_sha256


def resolve_storage_key(storage_key: str) -> Path:
    """Resolve an asset storage key without allowing path traversal."""
    root = get_storage_root()
    candidate = (root / storage_key).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("Storage key resolves outside the configured storage root") from exc
    return candidate


def verify_asset_fixity(storage_key: str, expected_checksum: str) -> tuple[bool, str | None, str]:
    """Return (matches, actual_checksum, detail) for a stored asset."""
    path = resolve_storage_key(storage_key)
    if not path.is_file():
        return False, None, f"Stored asset not found at storage key: {storage_key}"

    actual = compute_sha256(path)
    if actual.lower() == expected_checksum.lower():
        return True, actual, "SHA-256 fixity verification passed."

    return False, actual, "SHA-256 fixity verification failed: stored content differs from the recorded checksum."
