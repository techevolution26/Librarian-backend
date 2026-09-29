from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ReaderCapabilityRead(BaseModel):
    feature_key: str
    enabled: bool
    limit_value: int | None


class ReaderCapabilitiesRead(BaseModel):
    plan_code: str
    capabilities: list[ReaderCapabilityRead]

    model_config = ConfigDict(from_attributes=True)
