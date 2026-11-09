from flask import Blueprint, jsonify, request

from .constants import RegistryType
from .errors import AuthError
from .middleware import require_auth
from .services import (
    check_registry,
    register_account,
    resend_confirmation_email,
    sign_in,
)
from .validators import email_address, optional_registry_type, password, required_string

auth = Blueprint("auth", __name__, url_prefix="/auth")


@auth.errorhandler(AuthError)
def handle_auth_error(error: AuthError):
    return jsonify({"error": error.message}), error.status_code


def _body() -> dict:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise AuthError("A JSON request body is required", 400)
    return payload


@auth.post("/check")
def check():
    payload = _body()
    email = email_address(payload)
    role = optional_registry_type(payload)
    action = payload.get("action")
    if action is not None:
        action = str(action).strip().lower()
    return jsonify(check_registry(email, registry_type=role, action=action))


@auth.post("/check-student")
def check_student():
    """Compatibility endpoint delegating to unified check logic."""
    payload = _body()
    email = email_address(payload)
    action = payload.get("action")
    return jsonify(check_registry(email, registry_type=RegistryType.STUDENT, action=action))


@auth.post("/check-faculty")
def check_faculty():
    """Compatibility endpoint delegating to unified check logic."""
    payload = _body()
    email = email_address(payload)
    action = payload.get("action")
    return jsonify(check_registry(email, registry_type=RegistryType.FACULTY, action=action))


@auth.post("/register")
def register():
    payload = _body()
    raw_password = password(payload)
    token = payload.get("registration_token")
    if token:
        token_str = str(token).strip()
        result = register_account(raw_password=raw_password, registration_token=token_str)
    else:
        email = email_address(payload)
        role = optional_registry_type(payload)
        result = register_account(
            raw_password=raw_password,
            email=email,
            registry_type=role,
        )
    return jsonify(result), 201


@auth.post("/login")
def login():
    payload = _body()
    email = email_address(payload)
    raw_password = required_string(payload, "password")
    role = optional_registry_type(payload)
    result = sign_in(email=email, raw_password=raw_password, registry_type=role)
    return jsonify(result), 200


@auth.post("/resend-confirmation")
def resend_confirmation():
    payload = _body()
    email = email_address(payload)
    result = resend_confirmation_email(email)
    return jsonify(result), 200


@auth.get("/me")
@require_auth
def me():
    from flask import g

    return jsonify({
        "user": {"id": g.current_user.id, "email": g.current_user.email},
        "profile": g.current_profile,
    })
