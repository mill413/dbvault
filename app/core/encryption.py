import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import get_settings


def _derive_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def get_fernet() -> Fernet:
    settings = get_settings()
    key = settings.encryption_key
    if key:
        return Fernet(key.encode("utf-8"))
    if settings.env.lower() == "prod":
        raise RuntimeError("DBVAULT_ENCRYPTION_KEY is required when DBVAULT_ENV=prod")
    return Fernet(_derive_key(settings.jwt_secret))


def encrypt_secret(value: str) -> str:
    return get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    return get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
