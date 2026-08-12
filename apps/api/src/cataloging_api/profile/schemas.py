import uuid
from datetime import datetime

from pydantic import BaseModel


class TopValueOut(BaseModel):
    value: str
    item_count: int
    value_count: int
    item_rate: float


class FieldProfileOut(BaseModel):
    field: str
    label: str
    item_count: int
    missing_item_count: int
    value_count: int
    distinct_value_count: int
    coverage_rate: float
    top_values: list[TopValueOut]


class CompletenessPatternOut(BaseModel):
    fields_present: list[str]
    item_count: int
    rate: float


class RelationshipPairOut(BaseModel):
    from_value: str
    to_value: str
    item_count: int
    item_rate: float


class RelationshipProfileOut(BaseModel):
    from_field: str
    to_field: str
    observed_pairs: int
    pairs: list[RelationshipPairOut]


class CollectionProfileOut(BaseModel):
    collection_uuid: uuid.UUID
    collection_name: str
    collection_handle: str | None
    generated_at: datetime
    source: str
    grain: str
    active_items: int
    latest_sync_status: str | None
    latest_sync_finished_at: datetime | None
    fields: list[FieldProfileOut]
    completeness_patterns: list[CompletenessPatternOut]
    relationships: list[RelationshipProfileOut]
    interpretation: str
