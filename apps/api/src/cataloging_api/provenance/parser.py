import hashlib
import hmac
import re

EMAIL = re.compile(r"[\w.+-]+@[\w.-]+", re.IGNORECASE)


def extract_actor(value: str, *, secret: str) -> dict | None:
    match = EMAIL.search(value)
    if match is None:
        return None
    email = match.group(0).strip().casefold()
    actor_key = hmac.new(secret.encode(), email.encode(), hashlib.sha256).hexdigest()
    return {
        "actor_key": actor_key,
        "actor_type": "provenance_actor",
        "confidence": 0.8 if "submitted" in value.casefold() else 0.6,
        "explanation": "Correo extraído de procedencia DSpace y pseudonimizado con HMAC.",
    }
