import re

from .errors import AuthError

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9-]{3,64}$")


def required_string(payload: dict, field: str, max_length: int = 256) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise AuthError(f"{field} is required")
    value = value.strip()
    if len(value) > max_length:
        raise AuthError(f"{field} is too long")
    return value


def registry_identifier(payload: dict, field: str) -> str:
    value = required_string(payload, field, max_length=64)
    if not _IDENTIFIER_PATTERN.fullmatch(value):
        raise AuthError(f"{field} has an invalid format")
    return value


def password(payload: dict) -> str:
    value = required_string(payload, "password", max_length=256)
    if len(value) < 12:
        raise AuthError("Password must be at least 12 characters")
    if value != payload.get("confirm_password"):
        raise AuthError("Passwords do not match")
    return value
