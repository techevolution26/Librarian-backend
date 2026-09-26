from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings
from app.core.storage import get_storage_root


@dataclass(frozen=True)
class StorageObject:
    provider: str
    storage_key: str
    bucket: str | None = None
    public_url: str | None = None


class StorageBackend(Protocol):
    """Contract for physical archival storage backends."""

    provider: str

    def resolve(self, storage_key: str) -> Path:
        """Resolve a stored object for local filesystem operations."""
        ...

    def exists(self, storage_key: str) -> bool: ...


class LocalStorageBackend:
    provider = "local"

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or get_storage_root()).resolve()

    def resolve(self, storage_key: str) -> Path:
        candidate = (self.root / storage_key).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ValueError(
                "Storage key resolves outside the configured storage root"
            ) from exc
        return candidate

    def exists(self, storage_key: str) -> bool:
        return self.resolve(storage_key).is_file()


def get_storage_backend() -> StorageBackend:
    """Return the configured physical-storage backend.

    Object-storage credentials and client dependencies are intentionally not
    introduced in this tackle. The abstraction is ready for a durable object
    storage implementation without changing BookAsset identity or its API.
    """
    provider = get_settings().storage_provider
    if provider == "local":
        return LocalStorageBackend()
    raise RuntimeError(
        f"Storage provider '{provider}' is configured but has no backend implementation yet."
    )
