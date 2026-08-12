import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.api.routes import (
    get_catalog_profile,
    get_controlled_vocabularies,
    get_item,
    get_item_metadata_validation,
    get_similar_items,
    get_suggestion_history,
    get_work_queue,
    latest_sync_run,
    search_active_items,
)


@dataclass(frozen=True)
class ToolResult:
    output: dict[str, Any]
    citations: list[dict[str, str]] = field(default_factory=list)


ToolHandler = Callable[[AsyncSession, dict[str, Any]], Awaitable[ToolResult]]


def _parse_uuid(args: dict[str, Any], key: str = "item_uuid") -> uuid.UUID | None:
    try:
        return uuid.UUID(str(args[key]))
    except (KeyError, ValueError, TypeError):
        return None


async def _search_items(session: AsyncSession, args: dict[str, Any]) -> ToolResult:
    size = min(max(int(args.get("size") or 10), 1), 25)
    result = await search_active_items(
        session,
        q=args.get("q") or None,
        linguistic_family=args.get("linguistic_family") or None,
        linguistic_branch=args.get("linguistic_branch") or None,
        linguistic_group=args.get("linguistic_group") or None,
        registered_language=args.get("registered_language") or None,
        size=size,
    )
    citations = [
        {"label": item.name, "target_path": f"/items/{item.uuid}"} for item in result.items[:5]
    ]
    return ToolResult(output=result.model_dump(mode="json"), citations=citations)


async def _get_item(session: AsyncSession, args: dict[str, Any]) -> ToolResult:
    item_uuid = _parse_uuid(args)
    if item_uuid is None:
        return ToolResult(output={"error": "item_uuid inválido o ausente"})
    try:
        detail = await get_item(item_uuid, session)
    except HTTPException as error:
        return ToolResult(output={"error": str(error.detail)})
    payload = detail.model_dump(mode="json")
    payload.pop("raw_json", None)
    return ToolResult(
        output=payload,
        citations=[{"label": detail.name, "target_path": f"/items/{item_uuid}"}],
    )


async def _get_similar_items(session: AsyncSession, args: dict[str, Any]) -> ToolResult:
    item_uuid = _parse_uuid(args)
    if item_uuid is None:
        return ToolResult(output={"error": "item_uuid inválido o ausente"})
    limit = min(max(int(args.get("limit") or 5), 1), 20)
    try:
        similar = await get_similar_items(item_uuid, session, limit=limit)
    except HTTPException as error:
        return ToolResult(output={"error": str(error.detail)})
    citations = [
        {"label": entry.name, "target_path": f"/items/{entry.uuid}"} for entry in similar.items[:5]
    ]
    return ToolResult(output=similar.model_dump(mode="json"), citations=citations)


async def _get_item_metadata_validation(session: AsyncSession, args: dict[str, Any]) -> ToolResult:
    item_uuid = _parse_uuid(args)
    if item_uuid is None:
        return ToolResult(output={"error": "item_uuid inválido o ausente"})
    validation = await get_item_metadata_validation(item_uuid, session)
    if validation is None:
        return ToolResult(output={"error": "Ítem activo no encontrado"})
    return ToolResult(
        output=validation.model_dump(mode="json"),
        citations=[{"label": "Validación de metadatos", "target_path": f"/items/{item_uuid}"}],
    )


async def _get_suggestion_history(session: AsyncSession, args: dict[str, Any]) -> ToolResult:
    item_uuid = _parse_uuid(args)
    if item_uuid is None:
        return ToolResult(output={"error": "item_uuid inválido o ausente"})
    try:
        history = await get_suggestion_history(item_uuid, session)
    except HTTPException as error:
        return ToolResult(output={"error": str(error.detail)})
    return ToolResult(
        output=history.model_dump(mode="json"),
        citations=[{"label": "Historial de sugerencias", "target_path": f"/items/{item_uuid}"}],
    )


async def _get_work_queue(session: AsyncSession, args: dict[str, Any]) -> ToolResult:
    size = min(max(int(args.get("size") or 10), 1), 25)
    queue = await get_work_queue(
        session,
        q=args.get("q") or None,
        severity=args.get("severity") or None,
        finding_code=args.get("finding_code") or None,
        review=args.get("review") or None,
        suggestion_filter=args.get("suggestions") or None,
        draft_filter=args.get("draft") or None,
        page=0,
        size=size,
    )
    if queue is None:
        return ToolResult(output={"error": "Colección piloto no encontrada"})
    return ToolResult(
        output=queue.model_dump(mode="json"),
        citations=[{"label": "Cola de trabajo", "target_path": "/work-queue"}],
    )


async def _get_catalog_profile(session: AsyncSession, _args: dict[str, Any]) -> ToolResult:
    try:
        profile = await get_catalog_profile(session)
    except HTTPException as error:
        return ToolResult(output={"error": str(error.detail)})
    return ToolResult(
        output=profile.model_dump(mode="json"),
        citations=[{"label": "Evidencia de colección", "target_path": "/catalog-profile"}],
    )


async def _get_controlled_vocabularies(session: AsyncSession, args: dict[str, Any]) -> ToolResult:
    vocabularies = await get_controlled_vocabularies(
        session, field=args.get("field") or None, include_history=False
    )
    return ToolResult(
        output=vocabularies.model_dump(mode="json"),
        citations=[{"label": "Vocabularios controlados", "target_path": "/controlled-terms"}],
    )


async def _get_sync_status(session: AsyncSession, _args: dict[str, Any]) -> ToolResult:
    try:
        run = await latest_sync_run(session)
    except HTTPException as error:
        return ToolResult(output={"error": str(error.detail)})
    return ToolResult(
        output={
            "run_id": str(run.run_id),
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "items_seen": run.items_seen,
            "items_changed": run.items_changed,
        },
        citations=[{"label": "Estado de sincronización", "target_path": "/work-queue"}],
    )


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler


TOOLS: list[ToolSpec] = [
    ToolSpec(
        name="search_items",
        description=(
            "Busca ítems activos de la colección piloto por texto libre o por valores "
            "exactos de los campos lingüísticos controlados. Úsala para encontrar ítems "
            "antes de pedir su detalle con get_item."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "q": {
                    "type": "string",
                    "description": "Texto libre sobre título, handle o metadatos",
                },
                "linguistic_family": {"type": "string"},
                "linguistic_branch": {"type": "string"},
                "linguistic_group": {"type": "string"},
                "registered_language": {"type": "string"},
                "size": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 25,
                    "description": "Máximo de resultados, por defecto 10",
                },
            },
        },
        handler=_search_items,
    ),
    ToolSpec(
        name="get_item",
        description=(
            "Detalle completo de un ítem: metadatos, diagnóstico vigente, revisiones "
            "humanas y borradores locales."
        ),
        input_schema={
            "type": "object",
            "properties": {"item_uuid": {"type": "string", "description": "UUID del ítem"}},
            "required": ["item_uuid"],
        },
        handler=_get_item,
    ),
    ToolSpec(
        name="get_similar_items",
        description=(
            "Ítems estructuralmente similares a un ítem dado, con evidencia de coincidencia."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "item_uuid": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20},
            },
            "required": ["item_uuid"],
        },
        handler=_get_similar_items,
    ),
    ToolSpec(
        name="get_item_metadata_validation",
        description=(
            "Compara los valores de los cuatro campos lingüísticos de un ítem contra los "
            "vocabularios controlados activos, campo por campo."
        ),
        input_schema={
            "type": "object",
            "properties": {"item_uuid": {"type": "string"}},
            "required": ["item_uuid"],
        },
        handler=_get_item_metadata_validation,
    ),
    ToolSpec(
        name="get_suggestion_history",
        description=(
            "Sugerencias generadas para un ítem y las decisiones humanas registradas sobre "
            "cada una."
        ),
        input_schema={
            "type": "object",
            "properties": {"item_uuid": {"type": "string"}},
            "required": ["item_uuid"],
        },
        handler=_get_suggestion_history,
    ),
    ToolSpec(
        name="get_work_queue",
        description=(
            "Cola de trabajo priorizada de la colección piloto, con filtros por severidad, "
            "código de regla, estado de revisión, sugerencias o borrador."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "q": {"type": "string"},
                "severity": {"type": "string", "enum": ["error", "warning"]},
                "finding_code": {"type": "string"},
                "review": {"type": "string", "enum": ["pending", "reviewed", "deferred"]},
                "suggestions": {"type": "string", "enum": ["pending", "none"]},
                "draft": {
                    "type": "string",
                    "enum": ["none", "open", "approved", "rejected", "superseded", "stale"],
                },
                "size": {"type": "integer", "minimum": 1, "maximum": 25},
            },
        },
        handler=_get_work_queue,
    ),
    ToolSpec(
        name="get_catalog_profile",
        description=(
            "Perfil cuantitativo de la colección piloto: cobertura, valores frecuentes, "
            "patrones de completitud y relaciones observadas entre campos."
        ),
        input_schema={"type": "object", "properties": {}},
        handler=_get_catalog_profile,
    ),
    ToolSpec(
        name="get_controlled_vocabularies",
        description="Vocabularios controlados locales activos, opcionalmente filtrados por campo.",
        input_schema={
            "type": "object",
            "properties": {"field": {"type": "string"}},
        },
        handler=_get_controlled_vocabularies,
    ),
    ToolSpec(
        name="get_sync_status",
        description="Estado y frescura de la última sincronización con DSpace.",
        input_schema={"type": "object", "properties": {}},
        handler=_get_sync_status,
    ),
]

TOOLS_BY_NAME: dict[str, ToolSpec] = {tool.name: tool for tool in TOOLS}


def tool_schemas() -> list[dict[str, Any]]:
    return [
        {"name": tool.name, "description": tool.description, "input_schema": tool.input_schema}
        for tool in TOOLS
    ]
