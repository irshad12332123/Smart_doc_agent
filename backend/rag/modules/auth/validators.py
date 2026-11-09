import re
from typing import Any

from .constants import RegistryType
from .errors import AuthError

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def required_string(payload: dict[str, Any], field: str, max_length: int = 256) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise AuthError(f"{field} is required", 400)
    value = value.strip()
    if len(value) > max_length:
        raise AuthError(f"{field} is too long", 400)
    return value


def email_address(payload: dict[str, Any], field: str = "email") -> str:
    # Support email under "email", "official_email", or "registered_email"
    val = (
        payload.get(field)
        or payload.get("official_email")
        or payload.get("registered_email")
        or payload.get("student_id")
        or payload.get("faculty_id")
    )
    if not isinstance(val, str) or not val.strip():
        raise AuthError("Email is required", 400)
    val = val.strip().lower()
    if len(val) > 256:
        raise AuthError("Email is too long", 400)
    if not _EMAIL_PATTERN.match(val):
        raise AuthError("Invalid email address format", 400)
    return val


def registry_identifier(payload: dict[str, Any], field: str) -> str:
    """Compatibility helper for existing callers."""
    return email_address(payload, field)


def password(payload: dict[str, Any]) -> str:
    value = required_string(payload, "password", max_length=256)
    if len(value) < 8:
        raise AuthError("Password must be at least 8 characters", 400)
    confirm = payload.get("confirm_password")
    if confirm is not None and value != confirm:
        raise AuthError("Passwords do not match", 400)
    return value


def optional_registry_type(payload: dict[str, Any]) -> RegistryType | None:
    role_val = payload.get("role") or payload.get("registry_type") or payload.get("type")
    if not role_val:
        return None
    try:
        return RegistryType(str(role_val).strip().lower())
    except ValueError:
        return None
