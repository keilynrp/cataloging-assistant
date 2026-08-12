import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ControlledTermCreate(BaseModel):
    value: str = Field(min_length=1, max_length=500)
    authority: str | None = Field(default=None, max_length=1000)
    language: str | None = Field(default=None, max_length=64)


class VocabularyRevisionCreate(BaseModel):
    request_id: uuid.UUID
    field: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=2, max_length=500)
    source_uri: str = Field(min_length=3, max_length=2000)
    version_label: str = Field(min_length=1, max_length=120)
    approved_by: str = Field(min_length=2, max_length=120)
    approval_note: str = Field(min_length=1, max_length=2000)
    terms: list[ControlledTermCreate] = Field(min_length=1, max_length=5000)


class ControlledTermOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    term_id: uuid.UUID
    value: str
    authority: str | None
    language: str | None
    position: int


class VocabularyRevisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    revision_id: uuid.UUID
    request_id: uuid.UUID
    field: str
    name: str
    source_uri: str
    version_label: str
    approved_by: str
    approval_note: str
    is_active: bool
    created_at: datetime
    terms: list[ControlledTermOut]


class VocabularyRevisionListOut(BaseModel):
    revisions: list[VocabularyRevisionOut]
    total: int


class ValidatedMetadataValueOut(BaseModel):
    value: str
    approved: bool
    matched_term: ControlledTermOut | None


class FieldVocabularyValidationOut(BaseModel):
    field: str
    status: Literal["no_vocabulary", "no_values", "valid", "invalid"]
    vocabulary: VocabularyRevisionOut | None
    values: list[ValidatedMetadataValueOut]


class ItemMetadataValidationOut(BaseModel):
    item_uuid: uuid.UUID
    source_hash: str
    status: Literal["not_configured", "valid", "invalid"]
    fields: list[FieldVocabularyValidationOut]
