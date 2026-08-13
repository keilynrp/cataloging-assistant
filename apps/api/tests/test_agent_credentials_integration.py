import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.agent import credentials as credentials_service
from cataloging_api.agent.providers.anthropic_provider import AnthropicProvider
from cataloging_api.agent.providers.openai_provider import OpenAIProvider
from cataloging_api.db.session import engine


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_credential_encrypts_the_key_and_only_exposes_a_masked_preview() -> None:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        credential = await credentials_service.create_credential(
            session,
            provider="anthropic",
            label="Prueba",
            model="claude-sonnet-5",
            api_key="sk-ant-abcdef1234567890",
            created_by="tester",
        )
        assert credential.encrypted_api_key != "sk-ant-abcdef1234567890"
        assert credential.key_preview == "sk-a••••••7890"
        assert credential.is_active is False
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_credential_rejects_an_unknown_provider_name() -> None:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        with pytest.raises(credentials_service.UnknownProviderNameError):
            await credentials_service.create_credential(
                session,
                provider="totally-unknown-vendor",
                label="Prueba",
                model="some-model",
                api_key="sk-abcdef1234567890",
                created_by="tester",
            )
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_activating_a_credential_deactivates_every_other_one() -> None:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        first = await credentials_service.create_credential(
            session,
            provider="anthropic",
            label="Primera",
            model="claude-sonnet-5",
            api_key="sk-ant-abcdef1234567890",
            created_by="tester",
        )
        second = await credentials_service.create_credential(
            session,
            provider="openai",
            label="Segunda",
            model="gpt-5",
            api_key="sk-openai-abcdef1234567890",
            created_by="tester",
        )

        await credentials_service.activate_credential(session, first.credential_id)
        active = await credentials_service.get_active_credential(session)
        assert active is not None
        assert active.credential_id == first.credential_id

        await credentials_service.activate_credential(session, second.credential_id)
        active = await credentials_service.get_active_credential(session)
        assert active is not None
        assert active.credential_id == second.credential_id

        refreshed_first = await session.get(type(first), first.credential_id)
        assert refreshed_first is not None
        assert refreshed_first.is_active is False
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_activate_unknown_credential_raises_not_found() -> None:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        with pytest.raises(credentials_service.CredentialNotFoundError):
            await credentials_service.activate_credential(session, uuid.uuid4())
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_active_provider_builds_the_matching_adapter_with_the_decrypted_key() -> None:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        assert await credentials_service.get_active_provider(session) is None

        anthropic_credential = await credentials_service.create_credential(
            session,
            provider="anthropic",
            label="Prueba",
            model="claude-sonnet-5",
            api_key="sk-ant-abcdef1234567890",
            created_by="tester",
        )
        await credentials_service.activate_credential(session, anthropic_credential.credential_id)

        provider = await credentials_service.get_active_provider(session)
        assert isinstance(provider, AnthropicProvider)
        assert provider.model == "claude-sonnet-5"

        openai_credential = await credentials_service.create_credential(
            session,
            provider="openai",
            label="Prueba OpenAI",
            model="gpt-5",
            api_key="sk-openai-abcdef1234567890",
            created_by="tester",
        )
        await credentials_service.activate_credential(session, openai_credential.credential_id)

        provider = await credentials_service.get_active_provider(session)
        assert isinstance(provider, OpenAIProvider)
        assert provider.model == "gpt-5"
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_deactivate_and_delete_credential() -> None:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        credential = await credentials_service.create_credential(
            session,
            provider="anthropic",
            label="Prueba",
            model="claude-sonnet-5",
            api_key="sk-ant-abcdef1234567890",
            created_by="tester",
        )
        await credentials_service.activate_credential(session, credential.credential_id)
        assert (await credentials_service.get_active_credential(session)) is not None

        await credentials_service.deactivate_credential(session, credential.credential_id)
        assert (await credentials_service.get_active_credential(session)) is None

        await credentials_service.delete_credential(session, credential.credential_id)
        remaining = await credentials_service.list_credentials(session)
        assert credential.credential_id not in {item.credential_id for item in remaining}
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
