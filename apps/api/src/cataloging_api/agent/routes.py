import json
import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.agent import credentials as credentials_service
from cataloging_api.agent.constants import MAX_MESSAGES_PER_CONVERSATION
from cataloging_api.agent.crypto import DecryptionFailedError, EncryptionNotConfiguredError
from cataloging_api.agent.metrics import build_metrics
from cataloging_api.agent.providers.registry import KNOWN_PROVIDERS
from cataloging_api.agent.service import (
    ConversationSummary,
    create_conversation,
    get_conversation,
    list_conversations,
    stream_message,
)
from cataloging_api.api.routes import require_review_token
from cataloging_api.config import get_settings
from cataloging_api.db.session import get_session

router = APIRouter(prefix="/api/agent", tags=["agent"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


class ConversationCreate(BaseModel):
    started_by: str = Field(min_length=2, max_length=120)


class ConversationOut(BaseModel):
    conversation_id: uuid.UUID
    started_by: str
    started_at: str
    status: str


class MessageOut(BaseModel):
    message_id: uuid.UUID
    role: str
    content: str
    citations: list[dict[str, str]]
    created_at: str


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut]


class ConversationSummaryOut(ConversationOut):
    message_count: int
    last_message_at: str | None


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class AgentMetricsOut(BaseModel):
    total_conversations: int
    conversations_by_status: dict[str, int]
    total_messages: int
    messages_by_role: dict[str, int]
    avg_messages_per_conversation: float | None
    tool_calls_by_tool: dict[str, int]
    total_input_tokens: int
    total_output_tokens: int
    avg_first_chunk_latency_ms: int | None
    turn_error_count: int
    turn_error_rate: float | None


class ProviderCredentialCreate(BaseModel):
    provider: str = Field(min_length=2, max_length=40)
    label: str = Field(min_length=2, max_length=120)
    model: str = Field(min_length=1, max_length=120)
    api_key: str = Field(min_length=8, max_length=400)
    created_by: str = Field(min_length=2, max_length=120)
    activate: bool = False


class ProviderCredentialOut(BaseModel):
    credential_id: uuid.UUID
    provider: str
    label: str
    model: str
    key_preview: str
    is_active: bool
    created_by: str
    created_at: str
    updated_at: str


def _conversation_out(conversation) -> ConversationOut:  # noqa: ANN001
    return ConversationOut(
        conversation_id=conversation.conversation_id,
        started_by=conversation.started_by,
        started_at=conversation.started_at.isoformat(),
        status=conversation.status,
    )


def _conversation_summary_out(summary: ConversationSummary) -> ConversationSummaryOut:
    base = _conversation_out(summary.conversation)
    return ConversationSummaryOut(
        **base.model_dump(),
        message_count=summary.message_count,
        last_message_at=summary.last_message_at.isoformat() if summary.last_message_at else None,
    )


def _credential_out(credential) -> ProviderCredentialOut:  # noqa: ANN001
    return ProviderCredentialOut(
        credential_id=credential.credential_id,
        provider=credential.provider,
        label=credential.label,
        model=credential.model,
        key_preview=credential.key_preview,
        is_active=credential.is_active,
        created_by=credential.created_by,
        created_at=credential.created_at.isoformat(),
        updated_at=credential.updated_at.isoformat(),
    )


async def _require_provider(session: AsyncSession):  # noqa: ANN202
    try:
        provider = await credentials_service.get_active_provider(session)
    except EncryptionNotConfiguredError as error:
        raise HTTPException(
            status_code=503,
            detail="El cifrado de credenciales no está configurado (SETTINGS_ENCRYPTION_KEY)",
        ) from error
    except DecryptionFailedError as error:
        raise HTTPException(
            status_code=503,
            detail="No se pudo descifrar la credencial activa; revísala en /settings",
        ) from error
    if provider is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "El agente conversacional no está configurado; "
                "añade una credencial en /settings"
            ),
        )
    return provider


@router.post(
    "/conversations",
    response_model=ConversationOut,
    status_code=201,
    dependencies=[Depends(require_review_token)],
)
async def post_conversation(payload: ConversationCreate, session: SessionDep) -> ConversationOut:
    collection_uuid = uuid.UUID(get_settings().dspace_pilot_collection_uuid)
    conversation = await create_conversation(
        session, started_by=payload.started_by, collection_uuid=collection_uuid
    )
    await session.commit()
    return _conversation_out(conversation)


@router.get("/conversations", response_model=list[ConversationSummaryOut])
async def get_conversations(session: SessionDep) -> list[ConversationSummaryOut]:
    summaries = await list_conversations(session)
    return [_conversation_summary_out(summary) for summary in summaries]


@router.get("/metrics", response_model=AgentMetricsOut)
async def get_agent_metrics(session: SessionDep) -> AgentMetricsOut:
    metrics = await build_metrics(session)
    return AgentMetricsOut(**metrics)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailOut)
async def get_conversation_detail(
    conversation_id: uuid.UUID, session: SessionDep
) -> ConversationDetailOut:
    conversation = await get_conversation(session, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    base = _conversation_out(conversation)
    return ConversationDetailOut(
        **base.model_dump(),
        messages=[
            MessageOut(
                message_id=message.message_id,
                role=message.role,
                content=message.content,
                citations=message.citations,
                created_at=message.created_at.isoformat(),
            )
            for message in conversation.messages
        ],
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    dependencies=[Depends(require_review_token)],
)
async def post_message(
    conversation_id: uuid.UUID, payload: MessageCreate, session: SessionDep
) -> StreamingResponse:
    provider = await _require_provider(session)

    conversation = await get_conversation(session, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    if len(conversation.messages) >= MAX_MESSAGES_PER_CONVERSATION:
        raise HTTPException(
            status_code=409, detail="Se alcanzó el límite de mensajes de esta conversación"
        )

    async def event_stream() -> AsyncIterator[str]:
        async for item in stream_message(
            session, conversation_id=conversation_id, content=payload.content, provider=provider
        ):
            data = json.dumps(item["data"], ensure_ascii=False)
            yield f"event: {item['event']}\ndata: {data}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get(
    "/settings/credentials",
    response_model=list[ProviderCredentialOut],
    dependencies=[Depends(require_review_token)],
)
async def list_provider_credentials(session: SessionDep) -> list[ProviderCredentialOut]:
    credentials = await credentials_service.list_credentials(session)
    return [_credential_out(credential) for credential in credentials]


@router.get(
    "/settings/providers",
    dependencies=[Depends(require_review_token)],
)
async def list_known_providers() -> list[str]:
    return list(KNOWN_PROVIDERS)


@router.post(
    "/settings/credentials",
    response_model=ProviderCredentialOut,
    status_code=201,
    dependencies=[Depends(require_review_token)],
)
async def post_provider_credential(
    payload: ProviderCredentialCreate, session: SessionDep
) -> ProviderCredentialOut:
    try:
        credential = await credentials_service.create_credential(
            session,
            provider=payload.provider,
            label=payload.label,
            model=payload.model,
            api_key=payload.api_key,
            created_by=payload.created_by,
        )
    except credentials_service.UnknownProviderNameError as error:
        raise HTTPException(
            status_code=422, detail=f"Proveedor desconocido: {error}"
        ) from error
    except EncryptionNotConfiguredError as error:
        raise HTTPException(
            status_code=503,
            detail="El cifrado de credenciales no está configurado (SETTINGS_ENCRYPTION_KEY)",
        ) from error
    if payload.activate:
        credential = await credentials_service.activate_credential(
            session, credential.credential_id
        )
    await session.commit()
    return _credential_out(credential)


@router.post(
    "/settings/credentials/{credential_id}/activate",
    response_model=ProviderCredentialOut,
    dependencies=[Depends(require_review_token)],
)
async def post_activate_credential(
    credential_id: uuid.UUID, session: SessionDep
) -> ProviderCredentialOut:
    try:
        credential = await credentials_service.activate_credential(session, credential_id)
    except credentials_service.CredentialNotFoundError as error:
        raise HTTPException(status_code=404, detail="Credencial no encontrada") from error
    await session.commit()
    return _credential_out(credential)


@router.post(
    "/settings/credentials/{credential_id}/deactivate",
    response_model=ProviderCredentialOut,
    dependencies=[Depends(require_review_token)],
)
async def post_deactivate_credential(
    credential_id: uuid.UUID, session: SessionDep
) -> ProviderCredentialOut:
    try:
        credential = await credentials_service.deactivate_credential(session, credential_id)
    except credentials_service.CredentialNotFoundError as error:
        raise HTTPException(status_code=404, detail="Credencial no encontrada") from error
    await session.commit()
    return _credential_out(credential)


@router.delete(
    "/settings/credentials/{credential_id}",
    status_code=204,
    dependencies=[Depends(require_review_token)],
)
async def delete_provider_credential(credential_id: uuid.UUID, session: SessionDep) -> None:
    try:
        await credentials_service.delete_credential(session, credential_id)
    except credentials_service.CredentialNotFoundError as error:
        raise HTTPException(status_code=404, detail="Credencial no encontrada") from error
    await session.commit()
