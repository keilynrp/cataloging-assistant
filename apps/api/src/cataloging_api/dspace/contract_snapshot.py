from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


COLLECTION_RELATIONS = {
    "metadata_schemas": "metadataschemas",
    "metadata_fields": "metadatafields",
    "submission_definitions": "submissiondefinitions",
    "submission_sections": "submissionsections",
    "submission_forms": "submissionforms",
    "active_submission_sections": "submissionsections",
}
REQUIRED_SURFACES = frozenset(
    {
        "metadata_schemas",
        "metadata_fields",
        "submission_forms",
        "active_submission_definition",
        "active_submission_sections",
    }
)


@dataclass(frozen=True)
class ContractSnapshotView:
    canonical: dict[str, Any]
    semantic_hash: str
    complete: bool
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class ContractChange:
    change_type: str
    severity: str
    identity: str
    before: Any = None
    after: Any = None


def _json_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _surface_items(surface: str, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    relation = COLLECTION_RELATIONS[surface]
    result: list[dict[str, Any]] = []
    for payload in payloads:
        embedded = payload.get("_embedded")
        values = embedded.get(relation) if isinstance(embedded, dict) else None
        if isinstance(values, list):
            result.extend(value for value in values if isinstance(value, dict))
    return result


def _schema_prefix(field: dict[str, Any]) -> str | None:
    direct = field.get("schema")
    if isinstance(direct, str) and direct:
        return direct
    embedded = field.get("_embedded")
    if isinstance(embedded, dict):
        schema = embedded.get("schema")
        if isinstance(schema, dict):
            prefix = schema.get("prefix")
            if isinstance(prefix, str) and prefix:
                return prefix
    for key in ("fullyQualifiedName", "fieldName", "name"):
        candidate = field.get(key)
        if isinstance(candidate, str) and candidate.count(".") >= 1:
            return candidate.split(".", 1)[0]
    return None


def _field_name(field: dict[str, Any], prefix: str) -> str | None:
    for key in ("fullyQualifiedName", "fieldName"):
        candidate = field.get(key)
        if isinstance(candidate, str) and candidate:
            return candidate
    element = field.get("element")
    if not isinstance(element, str) or not element:
        return None
    qualifier = field.get("qualifier")
    return f"{prefix}.{element}.{qualifier}" if isinstance(qualifier, str) and qualifier else f"{prefix}.{element}"


def _canonical_fields(
    fields: list[dict[str, Any]], warnings: list[str]
) -> list[dict[str, Any]]:
    canonical: list[dict[str, Any]] = []
    for field in fields:
        prefix = _schema_prefix(field)
        if prefix is None:
            warnings.append(f"UNRESOLVED_FIELD_SCHEMA:{field.get('id', 'unknown')}")
            continue
        name = _field_name(field, prefix)
        if name is None:
            warnings.append(f"UNRESOLVED_FIELD_NAME:{field.get('id', 'unknown')}")
            continue
        canonical.append(
            {
                "metadata": name,
                "id": field.get("id"),
                "scopeNote": field.get("scopeNote"),
            }
        )
    return sorted(canonical, key=lambda item: (item["metadata"], str(item.get("id"))))


def _active_form_ids(
    sections: list[dict[str, Any]], warnings: list[str]
) -> list[str]:
    result: list[str] = []
    for section in sections:
        if section.get("sectionType") != "submission-form":
            continue
        links = section.get("_links")
        config = links.get("config") if isinstance(links, dict) else None
        href = config.get("href") if isinstance(config, dict) else None
        if isinstance(href, str) and href.rstrip("/"):
            result.append(href.rstrip("/").rsplit("/", 1)[-1])
            continue
        section_id = section.get("id")
        if isinstance(section_id, str) and section_id:
            # DSpace's standard DescribeStep uses the same id for section and form.
            result.append(section_id)
        else:
            warnings.append("UNRESOLVED_SUBMISSION_FORM_LINK")
    return result


def _canonical_bindings(
    forms: list[dict[str, Any]], active_form_ids: list[str], warnings: list[str]
) -> list[dict[str, Any]]:
    forms_by_id = {
        str(form.get("id") or form.get("name")): form
        for form in forms
        if form.get("id") or form.get("name")
    }
    bindings: list[dict[str, Any]] = []
    for form_order, form_id in enumerate(active_form_ids):
        form = forms_by_id.get(form_id)
        if form is None:
            warnings.append(f"UNRESOLVED_ACTIVE_FORM:{form_id}")
            continue
        rows = form.get("rows")
        if not isinstance(rows, list):
            warnings.append(f"UNRESOLVED_FORM_ROWS:{form_id}")
            continue
        for row_index, row in enumerate(rows):
            fields = row.get("fields") if isinstance(row, dict) else None
            if not isinstance(fields, list):
                continue
            for field_index, field in enumerate(fields):
                if not isinstance(field, dict):
                    continue
                selectable = field.get("selectableMetadata")
                if not isinstance(selectable, list):
                    continue
                input_spec = field.get("input")
                input_type = input_spec.get("type") if isinstance(input_spec, dict) else None
                for option_index, option in enumerate(selectable):
                    if not isinstance(option, dict) or not isinstance(option.get("metadata"), str):
                        continue
                    bindings.append(
                        {
                            "bindingKey": f"{form_id}:{row_index}:{field_index}:{option_index}",
                            "form": form_id,
                            "formOrder": form_order,
                            "row": row_index,
                            "field": field_index,
                            "option": option_index,
                            "metadata": option["metadata"],
                            "label": field.get("label"),
                            "selectorLabel": option.get("label"),
                            "required": bool(field.get("mandatory", False)),
                            "repeatable": bool(field.get("repeatable", False)),
                            "inputType": input_type,
                            "controlledVocabulary": option.get("controlledVocabulary"),
                            "closed": option.get("closed"),
                            "typeBind": field.get("typeBind") if isinstance(field.get("typeBind"), list) else [],
                        }
                    )
    return sorted(bindings, key=lambda item: item["bindingKey"])


def build_contract_snapshot(
    pages_by_surface: dict[str, list[dict[str, Any]]]
) -> ContractSnapshotView:
    warnings: list[str] = []
    missing = sorted(REQUIRED_SURFACES - pages_by_surface.keys())
    warnings.extend(f"UNOBSERVABLE_SURFACE:{surface}" for surface in missing)

    fields = _surface_items("metadata_fields", pages_by_surface.get("metadata_fields", []))
    forms = _surface_items("submission_forms", pages_by_surface.get("submission_forms", []))
    active_sections = _surface_items(
        "active_submission_sections", pages_by_surface.get("active_submission_sections", [])
    )
    active_definition_payloads = pages_by_surface.get("active_submission_definition", [])
    active_definition = active_definition_payloads[0] if active_definition_payloads else {}
    active_definition_name = active_definition.get("name")
    if not isinstance(active_definition_name, str) or not active_definition_name:
        warnings.append("UNRESOLVED_ACTIVE_DEFINITION")

    active_form_ids = _active_form_ids(active_sections, warnings)
    canonical = {
        "activeDefinition": active_definition_name,
        "fields": _canonical_fields(fields, warnings),
        "bindings": _canonical_bindings(forms, active_form_ids, warnings),
    }
    unique_warnings = tuple(sorted(set(warnings)))
    complete = not unique_warnings
    return ContractSnapshotView(
        canonical=canonical,
        semantic_hash=_json_hash(canonical),
        complete=complete,
        warnings=unique_warnings,
    )


def diff_contract_snapshots(
    previous: ContractSnapshotView,
    current: ContractSnapshotView,
) -> list[ContractChange]:
    changes: list[ContractChange] = []
    if not current.complete:
        for warning in current.warnings:
            changes.append(ContractChange("UNOBSERVABLE_SURFACE", "CRITICAL", warning))

    old_fields = {item["metadata"]: item for item in previous.canonical.get("fields", [])}
    new_fields = {item["metadata"]: item for item in current.canonical.get("fields", [])}
    for key in sorted(new_fields.keys() - old_fields.keys()):
        changes.append(ContractChange("FIELD_ADDED", "INFO", key, after=new_fields[key]))
    if current.complete:
        for key in sorted(old_fields.keys() - new_fields.keys()):
            changes.append(ContractChange("FIELD_REMOVED", "CRITICAL", key, before=old_fields[key]))
    for key in sorted(old_fields.keys() & new_fields.keys()):
        old, new = old_fields[key], new_fields[key]
        if old.get("id") != new.get("id"):
            changes.append(ContractChange("FIELD_ID_CHANGED", "HIGH", key, old.get("id"), new.get("id")))
        if old.get("scopeNote") != new.get("scopeNote"):
            changes.append(ContractChange("FIELD_CHANGED", "LOW", key, old, new))

    old_bindings = {item["bindingKey"]: item for item in previous.canonical.get("bindings", [])}
    new_bindings = {item["bindingKey"]: item for item in current.canonical.get("bindings", [])}
    for key in sorted(new_bindings.keys() - old_bindings.keys()):
        changes.append(ContractChange("BINDING_ADDED", "MEDIUM", key, after=new_bindings[key]))
    if current.complete:
        for key in sorted(old_bindings.keys() - new_bindings.keys()):
            changes.append(ContractChange("BINDING_REMOVED", "CRITICAL", key, before=old_bindings[key]))
    for key in sorted(old_bindings.keys() & new_bindings.keys()):
        old, new = old_bindings[key], new_bindings[key]
        if old == new:
            continue
        specific = []
        if old.get("label") != new.get("label"):
            specific.append(("LABEL_CHANGED", "LOW"))
        if old.get("required") != new.get("required"):
            specific.append(("REQUIRED_CHANGED", "HIGH"))
        if old.get("repeatable") != new.get("repeatable"):
            specific.append(("REPEATABLE_CHANGED", "HIGH"))
        if old.get("inputType") != new.get("inputType"):
            specific.append(("INPUT_TYPE_CHANGED", "HIGH"))
        if old.get("controlledVocabulary") != new.get("controlledVocabulary") or old.get("closed") != new.get("closed"):
            specific.append(("VOCABULARY_CHANGED", "HIGH"))
        if not specific:
            specific.append(("BINDING_CHANGED", "MEDIUM"))
        for change_type, severity in specific:
            changes.append(ContractChange(change_type, severity, key, old, new))

    if previous.canonical.get("activeDefinition") != current.canonical.get("activeDefinition"):
        changes.append(
            ContractChange(
                "FORM_STRUCTURE_CHANGED",
                "HIGH",
                "activeDefinition",
                previous.canonical.get("activeDefinition"),
                current.canonical.get("activeDefinition"),
            )
        )
    return changes
