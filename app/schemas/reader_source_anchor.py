from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _LocatorBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PdfPageLocator(_LocatorBase):
    type: Literal["pdf_page"]
    asset_id: int = Field(gt=0)
    page_number: int = Field(ge=1)


class PdfTextLocator(_LocatorBase):
    """A page-local text range in a specific immutable PDF asset version."""

    type: Literal["pdf_text"]
    asset_id: int = Field(gt=0)
    page_number: int = Field(ge=1)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)
    offset_unit: Literal["unicode_codepoint"] = "unicode_codepoint"

    @model_validator(mode="after")
    def validate_range(self) -> "PdfTextLocator":
        if self.end_offset <= self.start_offset:
            raise ValueError("end_offset must be greater than start_offset")
        return self


class IIIFCanvasLocator(_LocatorBase):
    type: Literal["iiif_canvas"]
    canvas_identifier: str = Field(min_length=1, max_length=120)

    @field_validator("canvas_identifier")
    @classmethod
    def validate_canvas_identifier(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("canvas_identifier must not be blank")
        return value


class ImageRegionLocator(_LocatorBase):
    type: Literal["image_region"]
    canvas_identifier: str = Field(min_length=1, max_length=120)
    x: float = Field(ge=0, allow_inf_nan=False)
    y: float = Field(ge=0, allow_inf_nan=False)
    width: float = Field(gt=0, allow_inf_nan=False)
    height: float = Field(gt=0, allow_inf_nan=False)
    coordinate_space: Literal["pixel", "percent"] = "pixel"

    @field_validator("canvas_identifier")
    @classmethod
    def validate_canvas_identifier(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("canvas_identifier must not be blank")
        return value

    @model_validator(mode="after")
    def validate_percent_region(self) -> "ImageRegionLocator":
        if self.coordinate_space == "percent" and (
            self.x + self.width > 100 or self.y + self.height > 100
        ):
            raise ValueError("percentage region must remain within the 0–100 canvas bounds")
        return self


class TextSpanLocator(_LocatorBase):
    """A source text range in the Book's current plain-text representation."""

    type: Literal["text_span"]
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)
    offset_unit: Literal["unicode_codepoint"] = "unicode_codepoint"

    @model_validator(mode="after")
    def validate_range(self) -> "TextSpanLocator":
        if self.end_offset <= self.start_offset:
            raise ValueError("end_offset must be greater than start_offset")
        return self


class OCRSpanLocator(_LocatorBase):
    """A text range in one verified OCR record for a specific IIIF canvas."""

    type: Literal["ocr_span"]
    canvas_identifier: str = Field(min_length=1, max_length=120)
    ocr_page_id: int = Field(gt=0)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)
    offset_unit: Literal["unicode_codepoint"] = "unicode_codepoint"

    @field_validator("canvas_identifier")
    @classmethod
    def validate_canvas_identifier(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("canvas_identifier must not be blank")
        return value

    @model_validator(mode="after")
    def validate_range(self) -> "OCRSpanLocator":
        if self.end_offset <= self.start_offset:
            raise ValueError("end_offset must be greater than start_offset")
        return self


class MediaTimeLocator(_LocatorBase):
    type: Literal["media_time"]
    canvas_identifier: str = Field(min_length=1, max_length=120)
    start_seconds: float = Field(ge=0, allow_inf_nan=False)
    end_seconds: float = Field(gt=0, allow_inf_nan=False)

    @field_validator("canvas_identifier")
    @classmethod
    def validate_canvas_identifier(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("canvas_identifier must not be blank")
        return value

    @model_validator(mode="after")
    def validate_range(self) -> "MediaTimeLocator":
        if self.end_seconds <= self.start_seconds:
            raise ValueError("end_seconds must be greater than start_seconds")
        return self


ReaderSourceLocator = Annotated[
    Union[
        PdfPageLocator,
        PdfTextLocator,
        IIIFCanvasLocator,
        ImageRegionLocator,
        TextSpanLocator,
        OCRSpanLocator,
        MediaTimeLocator,
    ],
    Field(discriminator="type"),
]


class ReaderSourceAnchorCreate(BaseModel):
    book_id: int = Field(gt=0)
    locator: ReaderSourceLocator


class ReaderSourceAnchorRead(BaseModel):
    id: int
    user_id: int
    book_id: int
    archival_object_id: int | None = None
    locator: ReaderSourceLocator
    source_persistent_identifier: str | None = None
    source_accession_number: str | None = None
    source_canvas_identifier: str | None = None
    source_asset_id: int | None = None
    source_asset_version: int | None = None
    source_asset_checksum_sha256: str | None = None
    source_text_sha256: str | None = None
    # Live resolution hint: the immutable source snapshot is still the current
    # representation. None means the locator has no versioned asset/text to compare.
    source_is_current: bool | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
