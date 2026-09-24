from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class IIIFMetadataValue(BaseModel):
    label: str
    value: str


class IIIFRights(BaseModel):
    statement: str | None = None
    license: str | None = None
    attribution: str | None = None


class IIIFReadyProfile(BaseModel):
    """IIIF Presentation 3.0 preparation data, not a rendered manifest."""

    id: str = Field(
        description="Stable archival identifier suitable for an IIIF resource id."
    )
    type: str = "Manifest"
    label: str
    description: str | None = None
    metadata: list[IIIFMetadataValue] = Field(default_factory=list)
    rights: IIIFRights = Field(default_factory=IIIFRights)
    required_statement: IIIFMetadataValue | None = Field(
        default=None, alias="requiredStatement"
    )
    provider: list[str] = Field(default_factory=list)
    homepage: str | None = None
    see_also: list[str] = Field(default_factory=list)
    part_count: int = 0
    canvas_ready: bool = False

    model_config = ConfigDict(populate_by_name=True)
