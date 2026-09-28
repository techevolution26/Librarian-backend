from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


CREATOR_RIGHTS_BASIS_VALUES = (
    "original_author",
    "copyright_holder",
    "authorized_representative",
    "licensed",
    "public_domain",
    "other",
)


class CreatorRightsDeclarationCreate(BaseModel):
    rights_basis: str = Field(min_length=1, max_length=40)
    rights_holder_name: str = Field(min_length=1, max_length=255)
    rights_statement: str = Field(min_length=1)
    territory: str | None = Field(default=None, max_length=255)
    license_name: str | None = Field(default=None, max_length=255)
    license_url: HttpUrl | None = None
    hosting_allowed: bool
    public_display_allowed: bool
    download_allowed: bool
    redistribution_allowed: bool
    commercial_use_allowed: bool
    derivative_use_allowed: bool
    declaration_note: str | None = None
    attestation_acknowledged: bool = False

    @field_validator("rights_basis")
    @classmethod
    def validate_basis(cls, value: str) -> str:
        value = value.strip()
        if value not in CREATOR_RIGHTS_BASIS_VALUES:
            raise ValueError("Invalid rights basis")
        return value

    @field_validator("rights_holder_name", "rights_statement", "territory", "license_name", "declaration_note")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        clean = value.strip()
        return clean or None


class CreatorRightsDeclarationRead(BaseModel):
    id: int
    submission_id: int
    creator_account_id: int
    version: int
    rights_basis: str
    rights_holder_name: str
    rights_statement: str
    territory: str | None
    license_name: str | None
    license_url: str | None
    hosting_allowed: bool
    public_display_allowed: bool
    download_allowed: bool
    redistribution_allowed: bool
    commercial_use_allowed: bool
    derivative_use_allowed: bool
    declaration_note: str | None
    attestation_text: str
    status: str
    declared_by_user_id: int
    declared_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
