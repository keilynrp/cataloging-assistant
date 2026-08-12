import uuid
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

FIELD_SPECS = (
    ("dc.subject.linguisticFamily", "Familia lingüística"),
    ("dc.subject.linguisticBranch", "Rama lingüística"),
    ("dc.subject.linguiscgroup", "Agrupación lingüística"),
    ("dc.description.registeredLanguage", "Lengua registrada"),
)
FIELD_KEYS = tuple(field for field, _label in FIELD_SPECS)
FIELD_LABELS = dict(FIELD_SPECS)
RELATIONSHIP_SPECS = (
    ("dc.subject.linguisticFamily", "dc.subject.linguisticBranch"),
    ("dc.subject.linguisticBranch", "dc.subject.linguiscgroup"),
    ("dc.subject.linguiscgroup", "dc.description.registeredLanguage"),
)


@dataclass(frozen=True)
class PatternMetric:
    fields_present: tuple[str, ...]
    item_count: int
    rate: float


def safe_rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def summarize_completeness_patterns(
    item_uuids: Iterable[uuid.UUID],
    field_presence: Iterable[tuple[uuid.UUID, str]],
) -> list[PatternMetric]:
    presence_by_item: dict[uuid.UUID, set[str]] = {item_uuid: set() for item_uuid in item_uuids}
    for item_uuid, field in field_presence:
        if item_uuid in presence_by_item and field in FIELD_LABELS:
            presence_by_item[item_uuid].add(field)

    counts = Counter(
        tuple(field for field in FIELD_KEYS if field in present)
        for present in presence_by_item.values()
    )
    total = len(presence_by_item)
    return [
        PatternMetric(fields_present=fields, item_count=count, rate=safe_rate(count, total))
        for fields, count in sorted(counts.items(), key=lambda entry: (-entry[1], entry[0]))
    ]
