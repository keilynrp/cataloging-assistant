import re
import unicodedata
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

FIELD_WEIGHTS = {
    "dc.subject.linguisticFamily": 0.15,
    "dc.subject.linguisticBranch": 0.20,
    "dc.subject.linguiscgroup": 0.25,
    "dc.description.registeredLanguage": 0.30,
}
TITLE_WEIGHT = 0.10
TOKEN_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)


@dataclass(frozen=True)
class SimilarityItem:
    uuid: uuid.UUID
    name: str
    metadata: Mapping[str, Sequence[str]]


@dataclass(frozen=True)
class SimilarityEvidence:
    kind: str
    field: str | None
    values: tuple[str, ...]
    contribution: float


@dataclass(frozen=True)
class SimilarityMatch:
    item_uuid: uuid.UUID
    score: float
    evidence: tuple[SimilarityEvidence, ...]


def rank_similar_items(
    source: SimilarityItem,
    candidates: Iterable[SimilarityItem],
    *,
    limit: int,
) -> list[SimilarityMatch]:
    matches: list[SimilarityMatch] = []
    source_title_tokens = title_tokens(source.name)

    for candidate in candidates:
        if candidate.uuid == source.uuid:
            continue
        evidence: list[SimilarityEvidence] = []
        score = 0.0

        for field, weight in FIELD_WEIGHTS.items():
            shared = _shared_metadata_values(
                source.metadata.get(field, ()), candidate.metadata.get(field, ())
            )
            if shared:
                contribution = round(weight, 4)
                score += contribution
                evidence.append(
                    SimilarityEvidence(
                        kind="metadata_value_match",
                        field=field,
                        values=shared,
                        contribution=contribution,
                    )
                )

        shared_tokens = tuple(sorted(source_title_tokens & title_tokens(candidate.name)))
        if len(shared_tokens) >= 2:
            union = source_title_tokens | title_tokens(candidate.name)
            contribution = round(TITLE_WEIGHT * len(shared_tokens) / len(union), 4)
            score += contribution
            evidence.append(
                SimilarityEvidence(
                    kind="title_token_overlap",
                    field="dc.title",
                    values=shared_tokens,
                    contribution=contribution,
                )
            )

        if evidence:
            matches.append(
                SimilarityMatch(
                    item_uuid=candidate.uuid,
                    score=round(min(score, 1.0), 4),
                    evidence=tuple(evidence),
                )
            )

    return sorted(matches, key=lambda match: (-match.score, str(match.item_uuid)))[:limit]


def title_tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return {token for token in TOKEN_PATTERN.findall(normalized) if len(token) >= 3}


def _shared_metadata_values(
    source_values: Sequence[str], candidate_values: Sequence[str]
) -> tuple[str, ...]:
    source = {_normalize_value(value): value.strip() for value in source_values if value.strip()}
    candidate_keys = {_normalize_value(value) for value in candidate_values if value.strip()}
    return tuple(sorted(source[key] for key in source.keys() & candidate_keys))


def _normalize_value(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())
