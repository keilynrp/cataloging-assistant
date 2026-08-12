import json
import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.agent.constants import MAX_MESSAGES_PER_CONVERSATION
from cataloging_api.agent.provider import AgentProvider
from cataloging_api.agent.service import (
    create_conversation,
    get_conversation,
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


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


def _conversation_out(conversation) -> ConversationOut:  # noqa: ANN001
    return ConversationOut(
        conversation_id=conversation.conversation_id,
        started_by=conversation.started_by,
        started_at=conversation.started_at.isoformat(),
        status=conversation.status,
    )


def _require_provider() -> AgentProvider:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=503, detail="El agente conversacional no está configurado"
        )
    return AgentProvider(api_key=settings.anthropic_api_key, model=settings.anthropic_model)


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
    provider = _require_provider()

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
