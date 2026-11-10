from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ResourceContributionAssetRead(BaseModel):
    id: int
    asset_role: Literal["primary", "canvas"]
    sequence: int
    original_filename: str
    mime_type: str
    size_bytes: int
    checksum_sha256: str
    label: str | None
    width: int | None
    height: int | None
    imported_asset_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResourceContributionRead(BaseModel):
    id: int
    contributor_user_id: int
    contributor_name: str | None = None
    material_type: str
    status: str
    title: str
    author_name: str
    description: str
    language: str
    genres: list[str]
    subjects: list[str]
    original_format: str
    archival_object_type: str
    origin: str | None
    era: str | None
    condition_notes: str | None
    source_institution: str | None
    source_collection: str | None
    shelfmark: str | None
    provenance_accession_number: str | None
    digitized_by: str | None
    digitization_method: str | None
    scanner_device: str | None
    preservation_master_format: str | None
    derivative_format: str | None
    software: str | None
    rights_statement: str
    rights_holder: str | None
    rights_basis: str
    rights_evidence: str | None
    contributor_note: str | None
    review_note: str | None
    reviewed_by_user_id: int | None
    reviewed_at: datetime | None
    submitted_at: datetime
    imported_book_id: int | None
    imported_book_visibility: str | None = None
    imported_book_archived: bool = False
    created_at: datetime
    updated_at: datetime
    assets: list[ResourceContributionAssetRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ResourceContributionListRead(BaseModel):
    items: list[ResourceContributionRead]
    total: int
    active_count: int = 0
    max_active: int = 5
    can_submit: bool = True


class ResourceContributionReviewUpdate(BaseModel):
    status: Literal["under_review", "changes_requested", "rejected"]
    review_note: str | None = Field(default=None, max_length=5000)


class ResourceContributionMetadataUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    author_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1, max_length=20000)
    language: str | None = Field(default=None, min_length=2, max_length=40)
    original_format: Literal["born-digital", "printed", "manuscript", "oral-transcription"] | None = None
    archival_object_type: Literal["book", "manuscript", "newspaper", "photograph", "map", "document", "oral_history", "other"] | None = None
    genres: list[str] | None = Field(default=None, max_length=30)
    subjects: list[str] | None = Field(default=None, max_length=30)
    origin: str | None = Field(default=None, max_length=255)
    era: str | None = Field(default=None, max_length=120)
    condition_notes: str | None = Field(default=None, max_length=5000)
    source_institution: str | None = Field(default=None, max_length=255)
    source_collection: str | None = Field(default=None, max_length=255)
    shelfmark: str | None = Field(default=None, max_length=255)
    provenance_accession_number: str | None = Field(default=None, max_length=100)
    digitized_by: str | None = Field(default=None, max_length=255)
    digitization_method: str | None = Field(default=None, max_length=255)
    scanner_device: str | None = Field(default=None, max_length=255)
    preservation_master_format: str | None = Field(default=None, max_length=100)
    derivative_format: str | None = Field(default=None, max_length=100)
    software: str | None = Field(default=None, max_length=255)
    rights_statement: Literal["public-domain", "cc-by", "all-rights-reserved", "restricted"] | None = None
    rights_holder: str | None = Field(default=None, max_length=255)
    rights_basis: Literal["created_by_contributor", "permission_granted", "public_domain", "open_license", "unknown"] | None = None
    rights_evidence: str | None = Field(default=None, max_length=1000)
    contributor_note: str | None = Field(default=None, max_length=5000)


class ResourceContributionApprovalRead(BaseModel):
    contribution: ResourceContributionRead
    book_id: int
    archival_object_id: int
    book_visibility: str
    rights_review_required: bool = True
