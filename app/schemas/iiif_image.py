from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class IIIFSize(BaseModel):
    type: str = "Size"
    width: int
    height: int


class IIIFTile(BaseModel):
    width: int
    height: int | None = None
    scaleFactors: list[int] = Field(default_factory=list)


class IIIFImageInfo(BaseModel):
    context: str = Field(alias="@context")
    id: str
    type: str = "ImageService3"
    protocol: str = "http://iiif.io/api/image"
    profile: str = "level1"
    width: int
    height: int
    rights: str | None = None
    extraQualities: list[str] = Field(default_factory=list)
    extraFormats: list[str] = Field(default_factory=list)
    extraFeatures: list[str] = Field(default_factory=list)
    preferredFormats: list[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)
