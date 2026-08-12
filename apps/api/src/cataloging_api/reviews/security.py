import secrets


def review_token_is_valid(configured_token: str, provided_token: str | None) -> bool:
    if not configured_token or not provided_token:
        return False
    return secrets.compare_digest(configured_token, provided_token)
