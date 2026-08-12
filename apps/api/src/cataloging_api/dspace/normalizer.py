import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

LINGUISTIC_FIELDS = (
    "dc.subject.linguisticFamily",
    "dc.subject.linguisticBranch",
    "dc.subject.linguiscgroup",
    "dc.description.registeredLanguage",
)


@dataclass(frozen=True)
class MetadataValueData:
    field: str
    value: str
    language: str | None
    authority: str | None
    confidence: int | None
    place: int


@dataclass(frozen=True)
class BitstreamData:
    uuid: uuid.UUID
    name: str
    mime_type: str | None
    size_bytes: int | None
    content_url: str | None
    raw_json: dict[str, Any]


@dataclass(frozen=True)
class BundleData:
    uuid: uuid.UUID
    name: str
    bitstreams: list[BitstreamData]
    raw_json: dict[str, Any]


@dataclass(frozen=True)
class ItemData:
    uuid: uuid.UUID
    collection_uuid: uuid.UUID
    handle: str | None
    name: str
    last_modified: datetime | None
    metadata_values: list[MetadataValueData]
    bundles: list[BundleData]
    raw_json: dict[str, Any]
    source_hash: str


def normalize_item(
    raw_item: dict[str, Any],
    *,
    collection_uuid: str,
    bundles: list[tuple[dict[str, Any], list[dict[str, Any]]]],
) -> ItemData:
    metadata_values: list[MetadataValueData] = []
    metadata = raw_item.get("metadata") or {}
    for field, values in metadata.items():
        if not isinstance(values, list):
            continue
        for fallback_place, entry in enumerate(values):
            if not isinstance(entry, dict) or entry.get("value") is None:
                continue
            metadata_values.append(
                MetadataValueData(
                    field=field,
                    value=str(entry["value"]),
                    language=entry.get("language"),
                    authority=entry.get("authority"),
                    confidence=entry.get("confidence"),
                    place=int(entry.get("place", fallback_place)),
                )
            )

    normalized_bundles = [normalize_bundle(bundle, bitstreams) for bundle, bitstreams in bundles]
    source_payload = {
        "item": raw_item,
        "bundles": [
            {"bundle": raw_bundle, "bitstreams": raw_bitstreams}
            for raw_bundle, raw_bitstreams in bundles
        ],
    }
    canonical = json.dumps(
        source_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return ItemData(
        uuid=uuid.UUID(raw_item["uuid"]),
        collection_uuid=uuid.UUID(collection_uuid),
        handle=raw_item.get("handle"),
        name=raw_item.get("name") or "(sin título)",
        last_modified=_parse_datetime(raw_item.get("lastModified")),
        metadata_values=metadata_values,
        bundles=normalized_bundles,
        raw_json=raw_item,
        source_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    )


def normalize_bundle(
    raw_bundle: dict[str, Any], raw_bitstreams: list[dict[str, Any]]
) -> BundleData:
    bitstreams = [
        BitstreamData(
            uuid=uuid.UUID(raw["uuid"]),
            name=raw.get("name") or "(sin nombre)",
            mime_type=(raw.get("bundleName") or raw.get("mimeType")),
            size_bytes=raw.get("sizeBytes"),
            content_url=raw.get("_links", {}).get("content", {}).get("href"),
            raw_json=raw,
        )
        for raw in raw_bitstreams
        if raw.get("uuid")
    ]
    return BundleData(
        uuid=uuid.UUID(raw_bundle["uuid"]),
        name=raw_bundle.get("name") or "UNKNOWN",
        bitstreams=bitstreams,
        raw_json=raw_bundle,
    )


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
