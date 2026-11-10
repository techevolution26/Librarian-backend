from datetime import datetime

from pydantic import BaseModel, ConfigDict



class PreservationStorageCopyRead(BaseModel):
    id: int
    asset_id: int
    provider: str
    bucket: str | None
    status: str
    is_primary: bool
    replicated_from_location_id: int | None
    replication_status: str
    replication_error: str | None
    checksum_sha256: str | None
    size_bytes: int | None
    created_at: datetime
    verified_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class PreservationAssetRead(BaseModel):
    id: int
    book_id: int
    asset_type: str
    asset_role: str
    logical_key: str | None
    version: int
    original_filename: str
    mime_type: str
    size_bytes: int
    checksum_sha256: str
    is_current: bool
    source_asset_id: int | None
    derivation_type: str | None
    created_at: datetime
    storage_locations: list[PreservationStorageCopyRead]

    model_config = ConfigDict(from_attributes=True)


class PreservationDashboardEventRead(BaseModel):
    id: int
    archival_object_id: int
    asset_id: int | None
    event_type: str
    event_date: datetime
    outcome: str
    agent: str | None
    detail: str | None
    checksum: str | None
    checksum_algorithm: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PreservationDashboardRead(BaseModel):
    archival_object_id: int
    assets: list[PreservationAssetRead]
    events: list[PreservationDashboardEventRead]
