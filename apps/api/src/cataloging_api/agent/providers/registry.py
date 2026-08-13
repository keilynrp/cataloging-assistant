from cataloging_api.agent.providers.anthropic_provider import AnthropicProvider
from cataloging_api.agent.providers.base import Provider
from cataloging_api.agent.providers.openai_provider import OpenAIProvider

_PROVIDER_FACTORIES = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
}

KNOWN_PROVIDERS: tuple[str, ...] = tuple(sorted(_PROVIDER_FACTORIES))


class UnknownProviderError(ValueError):
    pass


def build_provider(*, provider: str, api_key: str, model: str) -> Provider:
    factory = _PROVIDER_FACTORIES.get(provider)
    if factory is None:
        raise UnknownProviderError(provider)
    return factory(api_key=api_key, model=model)
