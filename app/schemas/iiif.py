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

    id: str = Field(description="Stable archival identifier suitable for an IIIF resource id.")
    type: str = "Manifest"
    label: str
    description: str | None = None
    metadata: list[IIIFMetadataValue] = Field(default_factory=list)
    rights: IIIFRights = Field(default_factory=IIIFRights)
    required_statement: IIIFMetadataValue | None = Field(default=None, alias="requiredStatement")
    provider: list[str] = Field(default_factory=list)
    homepage: str | None = None
    see_also: list[str] = Field(default_factory=list)
    part_count: int = 0
    canvas_ready: bool = False

    model_config = ConfigDict(populate_by_name=True)


class IIIFLanguageMap(BaseModel):
    en: list[str]


class IIIFManifestMetadata(BaseModel):
    label: IIIFLanguageMap
    value: IIIFLanguageMap


class IIIFRequiredStatement(BaseModel):
    label: IIIFLanguageMap
    value: IIIFLanguageMap


class IIIFProvider(BaseModel):
    id: str | None = None
    type: str = "Agent"
    label: IIIFLanguageMap


class IIIFSeeAlso(BaseModel):
    id: str
    type: str
    format: str | None = None


class IIIFImageService(BaseModel):
    id: str
    type: str = "ImageService3"
    profile: str = "level1"


class IIIFImageBody(BaseModel):
    id: str
    type: str = "Image"
    format: str
    width: int | None = None
    height: int | None = None
    service: list[IIIFImageService] = Field(default_factory=list)


class IIIFPaintingAnnotation(BaseModel):
    id: str
    type: str = "Annotation"
    motivation: str = "painting"
    body: IIIFImageBody


class IIIFAnnotationPage(BaseModel):
    id: str
    type: str = "AnnotationPage"
    items: list[IIIFPaintingAnnotation] = Field(default_factory=list)


class IIIFCanvas(BaseModel):
    id: str
    type: str = "Canvas"
    label: IIIFLanguageMap
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    items: list[IIIFAnnotationPage] = Field(default_factory=list)
    see_also: list[IIIFSeeAlso] | None = Field(default=None, alias="seeAlso")

    model_config = ConfigDict(populate_by_name=True)


class IIIFManifest(BaseModel):
    """IIIF Presentation 3.0 Manifest generated from the archival model."""

    context: str = Field(
        default="http://iiif.io/api/presentation/3/context.json",
        alias="@context",
    )
    id: str
    type: str = "Manifest"
    label: IIIFLanguageMap
    description: IIIFLanguageMap | None = None
    metadata: list[IIIFManifestMetadata] = Field(default_factory=list)
    rights: str | None = None
    required_statement: IIIFRequiredStatement | None = Field(default=None, alias="requiredStatement")
    provider: list[IIIFProvider] = Field(default_factory=list)
    homepage: list[IIIFSeeAlso] | None = None
    see_also: list[IIIFSeeAlso] | None = Field(default=None, alias="seeAlso")
    items: list[IIIFCanvas] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)
