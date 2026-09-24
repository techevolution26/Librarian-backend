from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class NotebookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=5000)

    @field_validator("title", "description")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class NotebookRead(BaseModel):
    id: int
    user_id: int
    title: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
