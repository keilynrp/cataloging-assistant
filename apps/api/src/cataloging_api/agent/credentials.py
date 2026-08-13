"""Service layer for ADR-011 provider credentials.

Mirrors the "single active row, deactivate-then-activate under a row lock"
pattern already used by ``vocabularies.service.replace_active_vocabulary`` —
no DB-level partial-unique-index, enforced by application logic only.
"""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.agent.crypto import decrypt_secret, encrypt_secret, mask_secret
from cataloging_api.agent.providers.base import Provider
from cataloging_api.agent.providers.registry import KNOWN_PROVIDERS, build_provider
from cataloging_api.config import get_settings
from cataloging_api.db.models import ProviderCredential


class UnknownProviderNameError(ValueError):
    pass


class CredentialNotFoundError(Exception):
    pass


async def list_credentials(session: AsyncSession) -> list[ProviderCredential]:
    result = await session.scalars(
        select(ProviderCredential).order_by(ProviderCredential.created_at.desc())
    )
    return list(result)


async def create_credential(
    session: AsyncSession,
    *,
    provider: str,
    label: str,
    model: str,
    api_key: str,
    created_by: str,
) -> ProviderCredential:
    provider = provider.strip().lower()
    if provider not in KNOWN_PROVIDERS:
        raise UnknownProviderNameError(provider)
    root_key = get_settings().settings_encryption_key
    credential = ProviderCredential(
        provider=provider,
        label=label.strip(),
        model=model.strip(),
        encrypted_api_key=encrypt_secret(root_key, api_key),
        key_preview=mask_secret(api_key),
        is_active=False,
        created_by=created_by.strip(),
    )
    session.add(credential)
    await session.flush()
    return credential


async def activate_credential(
    session: AsyncSession, credential_id: uuid.UUID
) -> ProviderCredential:
    credential = await session.get(ProviderCredential, credential_id)
    if credential is None:
        raise CredentialNotFoundError
    await session.execute(
        select(ProviderCredential).where(ProviderCredential.is_active.is_(True)).with_for_update()
    )
    await session.execute(
        update(ProviderCredential)
        .where(ProviderCredential.is_active.is_(True))
        .values(is_active=False)
    )
    credential.is_active = True
    await session.flush()
    return credential


async def deactivate_credential(
    session: AsyncSession, credential_id: uuid.UUID
) -> ProviderCredential:
    credential = await session.get(ProviderCredential, credential_id)
    if credential is None:
        raise CredentialNotFoundError
    credential.is_active = False
    await session.flush()
    return credential


async def delete_credential(session: AsyncSession, credential_id: uuid.UUID) -> None:
    credential = await session.get(ProviderCredential, credential_id)
    if credential is None:
        raise CredentialNotFoundError
    await session.delete(credential)
    await session.flush()


async def get_active_credential(session: AsyncSession) -> ProviderCredential | None:
    return await session.scalar(
        select(ProviderCredential).where(ProviderCredential.is_active.is_(True))
    )


async def get_active_provider(session: AsyncSession) -> Provider | None:
    credential = await get_active_credential(session)
    if credential is None:
        return None
    root_key = get_settings().settings_encryption_key
    api_key = decrypt_secret(root_key, credential.encrypted_api_key)
    return build_provider(provider=credential.provider, api_key=api_key, model=credential.model)
