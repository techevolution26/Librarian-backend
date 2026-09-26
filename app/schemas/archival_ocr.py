from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ArchivalOCRRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    archival_object_id: int
    canvas_id: int
    source_asset_id: int
    source_checksum_sha256: str
    text: str
    language: str
    engine: str
    engine_version: str
    status: str
    verified_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ArchivalOCRGenerateRequest(BaseModel):
    language: str = Field(default="eng", min_length=2, max_length=32, pattern=r"^[a-z0-9_+-]+$")
