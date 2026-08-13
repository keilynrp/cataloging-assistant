"""Encrypts provider API keys at rest (ADR-011).

Uses Fernet (symmetric, authenticated) with a root key from
``SETTINGS_ENCRYPTION_KEY``. Generate one with:
``python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"``
"""

from cryptography.fernet import Fernet, InvalidToken


class EncryptionNotConfiguredError(Exception):
    """SETTINGS_ENCRYPTION_KEY is unset; secret writes and reads are disabled."""


class DecryptionFailedError(Exception):
    """The stored ciphertext doesn't match the current root key (rotated or corrupted)."""


def encrypt_secret(root_key: str, plaintext: str) -> str:
    if not root_key:
        raise EncryptionNotConfiguredError
    return Fernet(root_key.encode()).encrypt(plaintext.encode()).decode()


def decrypt_secret(root_key: str, ciphertext: str) -> str:
    if not root_key:
        raise EncryptionNotConfiguredError
    try:
        return Fernet(root_key.encode()).decrypt(ciphertext.encode()).decode()
    except InvalidToken as error:
        raise DecryptionFailedError from error


def mask_secret(plaintext: str) -> str:
    if len(plaintext) <= 8:
        return "•" * len(plaintext)
    return f"{plaintext[:4]}{'•' * 6}{plaintext[-4:]}"
