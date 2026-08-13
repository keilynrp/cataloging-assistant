import pytest
from cryptography.fernet import Fernet

from cataloging_api.agent.crypto import (
    DecryptionFailedError,
    EncryptionNotConfiguredError,
    decrypt_secret,
    encrypt_secret,
    mask_secret,
)

ROOT_KEY = Fernet.generate_key().decode()
OTHER_KEY = Fernet.generate_key().decode()


def test_encrypt_then_decrypt_round_trips() -> None:
    ciphertext = encrypt_secret(ROOT_KEY, "sk-ant-super-secret")
    assert ciphertext != "sk-ant-super-secret"
    assert decrypt_secret(ROOT_KEY, ciphertext) == "sk-ant-super-secret"


def test_decrypt_with_the_wrong_root_key_fails() -> None:
    ciphertext = encrypt_secret(ROOT_KEY, "sk-ant-super-secret")
    with pytest.raises(DecryptionFailedError):
        decrypt_secret(OTHER_KEY, ciphertext)


def test_encrypt_without_a_configured_root_key_is_refused() -> None:
    with pytest.raises(EncryptionNotConfiguredError):
        encrypt_secret("", "sk-ant-super-secret")


def test_decrypt_without_a_configured_root_key_is_refused() -> None:
    with pytest.raises(EncryptionNotConfiguredError):
        decrypt_secret("", "anything")


def test_mask_secret_keeps_prefix_and_suffix_only() -> None:
    assert mask_secret("sk-ant-api03-abcdef1234567890") == "sk-a••••••7890"


def test_mask_secret_fully_masks_short_values() -> None:
    assert mask_secret("short") == "•••••"
