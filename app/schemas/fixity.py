from datetime import datetime

from pydantic import BaseModel

from app.schemas.preservation_event import PreservationEventRead


class FixityVerificationRead(BaseModel):
    asset_id: int
    archival_object_id: int
    expected_checksum: str
    actual_checksum: str | None
    matches: bool
    verified_at: datetime
    event: PreservationEventRead


class ObjectFixityVerificationRead(BaseModel):
    archival_object_id: int
    verified_at: datetime
    checked: int
    passed: int
    failed: int
    results: list[FixityVerificationRead]
