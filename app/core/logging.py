import logging
import re

from app.core.config import get_settings

SECRET_PATTERNS = [
    re.compile(r"(--password=)[^\s]+", re.IGNORECASE),
    re.compile(r"(PGPASSWORD=)[^\s]+", re.IGNORECASE),
    re.compile(r"(password['\"]?\s*[:=]\s*['\"]?)[^'\"\s,}]+", re.IGNORECASE),
    re.compile(r"(secret_key['\"]?\s*[:=]\s*['\"]?)[^'\"\s,}]+", re.IGNORECASE),
    re.compile(r"(access_token['\"]?\s*[:=]\s*['\"]?)[^'\"\s,}]+", re.IGNORECASE),
]


def configure_logging() -> None:
    logging.basicConfig(
        level=get_settings().log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def mask_secret(value: str | None) -> str | None:
    if value is None:
        return None
    masked = value
    for pattern in SECRET_PATTERNS:
        masked = pattern.sub(r"\1***", masked)
    return masked

