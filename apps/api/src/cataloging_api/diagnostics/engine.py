import hashlib
import json
import unicodedata
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

RULE_SET_VERSION = "2026-08-15.1"

LINGUISTIC_FAMILY = "dc.subject.linguisticFamily"
LINGUISTIC_BRANCH = "dc.subject.linguisticBranch"
LINGUISTIC_GROUP = "dc.subject.linguiscgroup"
LINGUISTIC_VARIANT = "dc.subject.linguisticVariant"
REGISTERED_LANGUAGE = "dc.description.registeredLanguage"

CONTROLLED_LINGUISTIC_FIELDS = (
    LINGUISTIC_FAMILY,
    LINGUISTIC_BRANCH,
    LINGUISTIC_GROUP,
    LINGUISTIC_VARIANT,
    REGISTERED_LANGUAGE,
)


@dataclass(frozen=True)
class VocabularyRule:
    revision_key: str
    name: str
    source_uri: str
    version_label: str
    approved_by: str
    terms: frozenset[str]

    @property
    def profile_key(self) -> str:
        return self.revision_key


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    affected_fields: tuple[str, ...]
    explanation: str
    rule_version: str = RULE_SET_VERSION
    evidence_key: str | None = None

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(
            {
                "code": self.code,
                "affected_fields": self.affected_fields,
                "evidence_key": self.evidence_key,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def diagnostic_profile_version(
    required_fields: Iterable[str] = (),
    vocabulary_revisions: Iterable[str] = (),
) -> str:
    """Version active rules plus reversible collection-level configuration."""
    payload = json.dumps(
        {
            "rule_set": RULE_SET_VERSION,
            "required_fields": sorted(set(required_fields)),
            "vocabulary_revisions": sorted(set(vocabulary_revisions)),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    suffix = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    return f"{RULE_SET_VERSION}+{suffix}"


def evaluate_metadata(
    metadata: Mapping[str, Sequence[str]],
    *,
    required_fields: Iterable[str] = (),
    vocabularies: Mapping[str, VocabularyRule] | None = None,
) -> list[Finding]:
    """Evaluate only deterministic rules approved for the current pilot profile.

    CLIN is modeled as Familia → Agrupación → Variante. ``Rama`` is an
    optional genealogical enrichment and therefore family-without-branch is not
    an error. ``Lengua de registro`` is the language of the resource and is not
    part of that subject hierarchy.
    """
    present_fields = {
        field for field, values in metadata.items() if any(value.strip() for value in values)
    }
    findings: list[Finding] = []

    if LINGUISTIC_BRANCH in present_fields and LINGUISTIC_FAMILY not in present_fields:
        findings.append(
            Finding(
                code="CAT-LING-002",
                severity="error",
                affected_fields=(LINGUISTIC_BRANCH, LINGUISTIC_FAMILY),
                explanation=(
                    "El registro contiene rama lingüística, pero no contiene familia "
                    "lingüística. La rama es un enriquecimiento genealógico opcional, "
                    "pero cuando se usa necesita contexto de familia."
                ),
            )
        )

    if LINGUISTIC_GROUP in present_fields and LINGUISTIC_FAMILY not in present_fields:
        findings.append(
            Finding(
                code="CAT-LING-004",
                severity="warning",
                affected_fields=(LINGUISTIC_GROUP, LINGUISTIC_FAMILY),
                explanation=(
                    "El registro contiene agrupación lingüística, pero no familia. "
                    "Para lenguas indígenas de México, revise la jerarquía CLIN "
                    "Familia → Agrupación → Variante."
                ),
            )
        )

    if LINGUISTIC_VARIANT in present_fields and LINGUISTIC_GROUP not in present_fields:
        findings.append(
            Finding(
                code="CAT-LING-005",
                severity="warning",
                affected_fields=(LINGUISTIC_VARIANT, LINGUISTIC_GROUP),
                explanation=(
                    "El registro contiene variante lingüística, pero no agrupación. "
                    "Revise la correspondencia de autoridad antes de aceptar la variante."
                ),
            )
        )

    for field in sorted(set(required_fields)):
        if field not in present_fields:
            findings.append(
                Finding(
                    code="CAT-META-001",
                    severity="error",
                    affected_fields=(field,),
                    explanation=(
                        f"El campo configurado como obligatorio para la colección está "
                        f"ausente o vacío: {field}."
                    ),
                )
            )

    # Repeated metadata values preserve their DSpace positions, but duplicate
    # literals after Unicode/case normalization are still reviewable data. The
    # rule deliberately does not infer value-to-value hierarchy across flat
    # repeatable fields.
    for field in CONTROLLED_LINGUISTIC_FIELDS:
        values = [value.strip() for value in metadata.get(field, ()) if value.strip()]
        normalized = [unicodedata.normalize("NFKC", value).casefold() for value in values]
        duplicates = sorted(value for value, count in Counter(normalized).items() if count > 1)
        if not duplicates:
            continue
        evidence_key = json.dumps(
            {"field": field, "normalized_duplicates": duplicates},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        findings.append(
            Finding(
                code="CAT-LING-003",
                severity="warning",
                affected_fields=(field,),
                explanation=(
                    "El campo contiene valores lingüísticos repetidos después de "
                    "normalizar espacios, Unicode y mayúsculas/minúsculas. Debe "
                    "revisarse sin alterar automáticamente el orden original."
                ),
                evidence_key=evidence_key,
            )
        )
    for field, vocabulary in sorted((vocabularies or {}).items()):
        values = {value.strip() for value in metadata.get(field, ()) if value.strip()}
        invalid_values = sorted(values - vocabulary.terms)
        if not invalid_values:
            continue
        shown = ", ".join(f"«{value}»" for value in invalid_values[:5])
        remaining = len(invalid_values) - 5
        if remaining > 0:
            shown = f"{shown} y {remaining} valor(es) adicional(es)"
        evidence_key = json.dumps(
            {
                "revision": vocabulary.revision_key,
                "invalid_values": invalid_values,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        revision_suffix = hashlib.sha256(vocabulary.revision_key.encode("utf-8")).hexdigest()[:12]
        findings.append(
            Finding(
                code="CAT-VOCAB-001",
                severity="warning",
                affected_fields=(field,),
                explanation=(
                    f"El valor no coincide literalmente con el vocabulario aprobado "
                    f"«{vocabulary.name}», versión {vocabulary.version_label}: {shown}. "
                    f"Fuente: {vocabulary.source_uri}."
                ),
                rule_version=f"{RULE_SET_VERSION}+v{revision_suffix}",
                evidence_key=evidence_key,
            )
        )

    return findings


def group_metadata_values(values: Iterable[tuple[str, str]]) -> dict[str, list[str]]:
    metadata: dict[str, list[str]] = {}
    for field, value in values:
        metadata.setdefault(field, []).append(value)
    return metadata
