from flask import current_app
from itsdangerous import BadData, URLSafeTimedSerializer

from config.settings import AUTH_REGISTRATION_TOKEN_MAX_AGE_SECONDS, AUTH_REGISTRATION_TOKEN_SECRET

from .errors import AuthError

_SALT = "smart-doc-agent.registration.v1"


def _serializer() -> URLSafeTimedSerializer:
    secret = AUTH_REGISTRATION_TOKEN_SECRET or current_app.secret_key
    if not secret:
        raise RuntimeError("AUTH_REGISTRATION_TOKEN_SECRET must be configured")
    return URLSafeTimedSerializer(secret_key=secret, salt=_SALT)


def create_registration_token(registry_type: str, email: str) -> str:
    return _serializer().dumps({"type": registry_type, "email": email, "registry_id": email})


def read_registration_token(token: str) -> dict[str, str]:
    try:
        payload = _serializer().loads(token, max_age=AUTH_REGISTRATION_TOKEN_MAX_AGE_SECONDS)
    except BadData as error:
        raise AuthError("Registration session is invalid or expired", 401) from error
    if not isinstance(payload, dict) or not payload.get("type"):
        raise AuthError("Registration session is invalid", 401)
    email = payload.get("email") or payload.get("registry_id")
    if not email:
        raise AuthError("Registration session is invalid", 401)
    return {"type": payload["type"], "email": email, "registry_id": email}
