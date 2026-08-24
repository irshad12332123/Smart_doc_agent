from flask import Blueprint, jsonify, request

from .constants import RegistryType
from .errors import AuthError
from .middleware import require_auth
from .services import check_registry, register_account, sign_in
from .validators import password, registry_identifier, required_string

auth = Blueprint("auth", __name__, url_prefix="/auth")


@auth.errorhandler(AuthError)
def handle_auth_error(error: AuthError):
    return jsonify({"error": error.message}), error.status_code


def _body() -> dict:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise AuthError("A JSON request body is required")
    return payload


@auth.post("/check-student")
def check_student():
    payload = _body()
    return jsonify(check_registry(RegistryType.STUDENT, registry_identifier(payload, "student_id")))


@auth.post("/check-faculty")
def check_faculty():
    payload = _body()
    return jsonify(check_registry(RegistryType.FACULTY, registry_identifier(payload, "faculty_id")))


@auth.post("/register")
def register():
    payload = _body()
    return jsonify(register_account(required_string(payload, "registration_token", 4096), password(payload))), 201


@auth.post("/login")
def login():
    payload = _body()
    # Registration is the only place that needs password confirmation.
    return jsonify(sign_in(required_string(payload, "email"), required_string(payload, "password")))


@auth.get("/me")
@require_auth
def me():
    from flask import g

    return jsonify({"user": {"id": g.current_user.id, "email": g.current_user.email}, "profile": g.current_profile})
