from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final

CONTRACT_VERSION: Final = "dspace-cataloger-v3.6"
DSpace_VERSION: Final = "7.6.6"

EVIDENCE_STATES: Final = (
    "EXTRAÍDO",
    "VERIFICADO",
    "INFERIDO",
    "GENERADO",
    "PENDIENTE",
    "APP_SCHEMA_GAP",
)


@dataclass(frozen=True)
class CatalogField:
    binding_id: str
    metadata_field: str
    ui_label: str
    assistant_label: str
    repeatable: bool = False
    required: bool = False
    controlled: bool = False
    vocabulary_id: str | None = None
    runtime_draftable: bool = False
    runtime_profiled: bool = False
    runtime_vocabularied: bool = False


FIELDS: Final = (
    CatalogField("provenance", "dcterms.provenance", "Provenance / Catalogación", "Provenance / Catalogación"),
    CatalogField("title", "dc.title", "Titulo", "Título", required=True),
    CatalogField("title-alternative", "dc.title.alternative", "Variante de título", "Variante de título"),
    CatalogField("title-subtitle", "dc.title.subtitle", "Subtítulo", "Subtítulo"),
    CatalogField("journal-title", "dc.relation.ispartof", "Título de revista", "Título de revista"),
    CatalogField("book-title", "dc.source.booktitle", "Es parte de (título del libro)", "Es parte de (título del libro)"),
    CatalogField("author", "dc.contributor.author", "Autor", "Autor", repeatable=True),
    CatalogField("translator", "dc.contributor.translator", "Traductor", "Traductor", repeatable=True),
    CatalogField("contributor-other", "dc.contributor.other", "Colaboradores", "Colaboradores", repeatable=True),
    CatalogField("contributor-institution", "dc.contributor.institution", "Instituciones participantes", "Instituciones participantes", repeatable=True),
    CatalogField("editor", "dc.contributor.editor", "Editores", "Editores", repeatable=True),
    CatalogField("date-issued", "dc.date.issued", "Fecha de Creacion", "Fecha de creación"),
    CatalogField("country-found", "dc.coverage.countryFound", "País donde se encontró el recurso", "País donde se encontró el recurso"),
    CatalogField("publisher", "dc.publisher", "Editorial", "Editorial", repeatable=True),
    CatalogField("issue", "dc.identifier.issue", "Edicion(No)/Periodicdad", "Edición / número / periodicidad"),
    CatalogField("issn", "dc.identifier.issn", "Identificador — ISSN", "Identificador — ISSN"),
    CatalogField("identifier-other", "dc.identifier.other", "Identificador — Otro", "Identificador — Otro"),
    CatalogField("ismn", "dc.identifier.ismn", "Identificador — ISMN", "Identificador — ISMN"),
    CatalogField("govdoc", "dc.identifier.govdoc", "Identificador — Documento gubernamental", "Identificador — Documento gubernamental"),
    CatalogField("uri", "dc.identifier.uri", "Identificador — URI", "Identificador — URI"),
    CatalogField("isbn", "dc.identifier.isbn", "Identificador — ISBN", "Identificador — ISBN"),
    CatalogField("eissn", "dc.identifier.eissn", "Identificador — eISSN", "Identificador — eISSN"),
    CatalogField("eisbn", "dc.identifier.eisbn", "Identificador — eISBN", "Identificador — eISBN"),
    CatalogField("handle", "dc.identifier.handle", "Identificador — Handle", "Identificador — Handle"),
    CatalogField("doi", "dc.identifier.doi", "Identificador — DOI", "Identificador — DOI"),
    CatalogField("source", "dc.source", "Fuente", "Fuente"),
    CatalogField("type", "dc.type", "Type", "Tipo", controlled=True, vocabulary_id="common_types"),
    CatalogField("language-usage", "dc.description.languageUsage", "Uso de lengua", "Uso de lengua", controlled=True, vocabulary_id="languageUsagePairs"),
    CatalogField(
        "registered-language",
        "dc.description.registeredLanguage",
        "Lengua de registro",
        "Lengua de registro",
        repeatable=True,
        controlled=True,
        vocabulary_id="registeredLanguagePairs",
        runtime_draftable=True,
        runtime_profiled=True,
        runtime_vocabularied=True,
    ),
    CatalogField(
        "linguistic-group",
        "dc.subject.linguiscgroup",
        "Lengua registrada (Agrupación lingüística)",
        "Agrupación lingüística",
        repeatable=True,
        controlled=True,
        vocabulary_id="linguiscgroupPairs",
        runtime_draftable=True,
        runtime_profiled=True,
        runtime_vocabularied=True,
    ),
    CatalogField(
        "linguistic-family",
        "dc.subject.linguisticFamily",
        "Familia lingüística",
        "Familia lingüística",
        repeatable=True,
        controlled=True,
        vocabulary_id="linguisticFamilyPairs",
        runtime_draftable=True,
        runtime_profiled=True,
        runtime_vocabularied=True,
    ),
    CatalogField(
        "linguistic-branch",
        "dc.subject.linguisticBranch",
        "Rama lingüística",
        "Rama lingüística",
        repeatable=True,
        controlled=True,
        vocabulary_id="linguisticBranchPairs",
        runtime_draftable=True,
        runtime_profiled=True,
        runtime_vocabularied=True,
    ),
    CatalogField(
        "linguistic-variant",
        "dc.subject.linguisticVariant",
        "Variante lingüística (CLIN)",
        "Variante lingüística (CLIN)",
        repeatable=True,
        controlled=True,
        vocabulary_id=None,
        runtime_draftable=True,
        runtime_profiled=True,
        runtime_vocabularied=True,
    ),
    CatalogField("self-denomination", "dc.subject.selfDenomination", "Autodenominación", "Autodenominación", controlled=True, vocabulary_id="selfDenominationPairs"),
    CatalogField("iso6391", "dc.language.iso6391", "ISO 639-1", "ISO 639-1", controlled=True, vocabulary_id="iso6391Pairs"),
    CatalogField("medium", "dc.format.medium", "Soporte", "Soporte", controlled=True, vocabulary_id="mediumPairs"),
    CatalogField("extent-type", "dc.format.medium", "Tipo de extensión", "Tipo de extensión", required=True, controlled=True, vocabulary_id="extentTypePairs"),
    CatalogField("extent", "dc.format.extent", "Número de páginas / extensión", "Número de páginas / extensión", required=True),
    CatalogField("rights", "dc.rights", "Derechos", "Derechos"),
    CatalogField("license", "dc.rights.license", "Licencia de uso", "Licencia de uso", controlled=True, vocabulary_id="licensePairs"),
    CatalogField("access-rights", "dc.rights.accessRights", "Derecho de acceso", "Derecho de acceso", controlled=True, vocabulary_id="accessRightsPairs"),
    CatalogField("physical-repository", "dc.source.physicalRepository", "Repositorio físico", "Repositorio físico", repeatable=True),
    CatalogField("digital-url", "dc.identifier.url", "Repositorio digital (URL)", "Repositorio digital (URL)", repeatable=True),
    CatalogField("primary-classification", "dc.subject.primaryClassification", "Clasificación primaria", "Clasificación primaria", controlled=True, vocabulary_id="primaryClassificationPairs"),
    CatalogField("keywords", "dc.subject", "Palabras Clave", "Palabras clave", repeatable=True, controlled=True, vocabulary_id="srsc"),
    CatalogField("abstract", "dc.description.abstract", "Abstract", "Resumen / Abstract"),
    CatalogField("education-level", "dc.audience.educationLevel", "Nivel educativo", "Nivel educativo", controlled=True, vocabulary_id="educationLevelPairs"),
    CatalogField("language-target", "dc.audience.languageTarget", "Para L1 o para L2", "Para L1 o para L2", controlled=True, vocabulary_id="languageTargetPairs"),
    CatalogField("topics", "dc.subject", "Tópicos (disciplinas, temas específicos)", "Tópicos", repeatable=True, controlled=True, vocabulary_id="topicsPairs"),
    CatalogField("coverage-country", "dc.coverage.country", "País", "País", repeatable=True),
    CatalogField("coverage-state", "dc.coverage.state", "Estado", "Estado", repeatable=True),
    CatalogField("coverage-region", "dc.coverage.region", "Región", "Región", repeatable=True),
    CatalogField("coverage-community", "dc.coverage.community", "Comunidad", "Comunidad", repeatable=True),
    CatalogField("coverage-temporal", "dc.coverage.temporal", "Temporal", "Cobertura temporal", repeatable=True),
    CatalogField("coverage-century", "dc.coverage.century", "Siglo", "Siglo", repeatable=True),
    CatalogField("description-notes", "dc.description", "Notas", "Notas"),
)

assert len(FIELDS) == 56

FIELD_BY_BINDING: Final = {field.binding_id: field for field in FIELDS}

# Runtime subsets are derived from the master contract to avoid drift across services.
DRAFTABLE_LINGUISTIC_FIELDS: Final = tuple(
    field.metadata_field for field in FIELDS if field.runtime_draftable
)
CONTROLLED_RUNTIME_FIELDS: Final = tuple(
    field.metadata_field for field in FIELDS if field.runtime_vocabularied
)
PROFILE_LINGUISTIC_FIELDS: Final = tuple(
    field.metadata_field for field in FIELDS if field.runtime_profiled
)
PROFILE_FIELD_LABELS: Final = {
    field.metadata_field: field.assistant_label
    for field in FIELDS
    if field.runtime_profiled
}

LINGUISTIC_FAMILY: Final = "dc.subject.linguisticFamily"
LINGUISTIC_BRANCH: Final = "dc.subject.linguisticBranch"
LINGUISTIC_GROUP: Final = "dc.subject.linguiscgroup"
LINGUISTIC_VARIANT: Final = "dc.subject.linguisticVariant"
REGISTERED_LANGUAGE: Final = "dc.description.registeredLanguage"

# CLIN normative axis. Branch is optional enrichment and registeredLanguage is independent.
CLIN_RELATIONSHIPS: Final = (
    (LINGUISTIC_FAMILY, LINGUISTIC_GROUP),
    (LINGUISTIC_GROUP, LINGUISTIC_VARIANT),
)
GENEALOGICAL_ENRICHMENT_RELATIONSHIPS: Final = (
    (LINGUISTIC_FAMILY, LINGUISTIC_BRANCH),
    (LINGUISTIC_BRANCH, LINGUISTIC_GROUP),
)
PROFILE_RELATIONSHIPS: Final = CLIN_RELATIONSHIPS + GENEALOGICAL_ENRICHMENT_RELATIONSHIPS

QA_RULES: Final = (
    "CAT-LING-002",
    "CAT-LING-003",
    "CAT-LING-004",
    "CAT-LING-005",
    "CAT-VOCAB-001",
    "CAT-META-001",
)


def contract_payload() -> dict[str, object]:
    return {
        "contract_version": CONTRACT_VERSION,
        "dspace_version": DSpace_VERSION,
        "field_count": len(FIELDS),
        "fields": [asdict(field) for field in FIELDS],
        "runtime": {
            "draftable_fields": list(DRAFTABLE_LINGUISTIC_FIELDS),
            "controlled_fields": list(CONTROLLED_RUNTIME_FIELDS),
            "profile_fields": list(PROFILE_LINGUISTIC_FIELDS),
            "profile_relationships": [list(pair) for pair in PROFILE_RELATIONSHIPS],
            "clin_relationships": [list(pair) for pair in CLIN_RELATIONSHIPS],
            "branch_is_optional_enrichment": True,
            "registered_language_is_independent": True,
            "dspace_write_enabled": False,
            "human_approval_required": True,
        },
        "evidence_states": list(EVIDENCE_STATES),
        "qa_rules": list(QA_RULES),
    }
