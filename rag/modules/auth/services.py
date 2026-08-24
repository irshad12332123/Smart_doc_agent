"""Server-side auth workflow.  This module never stores or logs passwords."""

from typing import Any

from lib.supabase import get_supabase_admin_client, get_supabase_client

from .constants import REGISTRY_CONFIG, GlobalRole, RegistryType
from .errors import AuthError
from .tokens import create_registration_token, read_registration_token


def _rows(response: Any) -> list[dict[str, Any]]:
    data = getattr(response, "data", response)
    return data if isinstance(data, list) else ([] if data is None else [data])


def _registry(registry_type: RegistryType, identifier: str) -> dict[str, Any] | None:
    config = REGISTRY_CONFIG[registry_type]
    response = (
        get_supabase_admin_client()
        .table(config["table"])
        .select("id, name, registered_email, profile_id")
        .eq(config["identifier_column"], identifier)
        .limit(1)
        .execute()
    )
    rows = _rows(response)
    return rows[0] if rows else None


def check_registry(registry_type: RegistryType, identifier: str) -> dict[str, Any]:
    record = _registry(registry_type, identifier)
    if not record:
        raise AuthError(f"{registry_type.value.title()} ID not found", 404)
    if record.get("profile_id"):
        return {"status": "registered", "message": "This ID already has an account."}

    return {
        "status": "eligible",
        "name": record["name"],
        "registered_email": record["registered_email"],
        "registration_token": create_registration_token(registry_type.value, identifier),
    }


def register_account(registration_token: str, raw_password: str) -> dict[str, str]:
    token = read_registration_token(registration_token)
    try:
        registry_type = RegistryType(token["type"])

    except (KeyError, ValueError) as error:
        raise AuthError("Registration session is invalid", 401) from error

    identifier = token["registry_id"]

    record = _registry(registry_type, identifier)

    if not record:
        raise AuthError("Eligibility record no longer exists", 404)
    if record.get("profile_id"):
        raise AuthError("This ID already has an account", 409)

    admin = get_supabase_admin_client()
    created_user_id: str | None = None
    try:
        # Supabase Auth hashes the password with its managed secure password
        # hashing implementation. Never pre-hash it here: that would become the
        # actual login password and weaken the authentication contract.
        created = admin.auth.admin.create_user(
            {"email": record["registered_email"], "password": raw_password, "email_confirm": True}
        )
        user = getattr(created, "user", None)
        created_user_id = getattr(user, "id", None)
        if not created_user_id:
            raise RuntimeError("Supabase did not return a new user id")

        config = REGISTRY_CONFIG[registry_type]
        # The SQL RPC locks the registry row and completes profile/linking in a
        # transaction, preventing two concurrent registrations for one ID.
        admin.rpc(
            "complete_registry_registration",
            {
                "p_registry_type": registry_type.value,
                "p_registry_id": record["id"],
                "p_profile_id": created_user_id,
                "p_full_name": record["name"],
                "p_role": config["role"].value,
            },
        ).execute()
    except Exception as error:
        if created_user_id:
            try:
                admin.auth.admin.delete_user(created_user_id)
            except Exception:
                # Keep the original error; failed cleanup is observable in server logs.
                pass
        message = str(error).lower()
        if "already" in message or "duplicate" in message:
            raise AuthError("This ID or email already has an account", 409) from error
        raise AuthError("Unable to create account. Please try again.", 502) from error

    return {"message": "Account created. You can now sign in.", "email": record["registered_email"]}


def sign_in(email: str, raw_password: str) -> dict[str, Any]:
    response = get_supabase_client().auth.sign_in_with_password(
        {"email": email, "password": raw_password}
    )
    session = getattr(response, "session", None)
    user = getattr(response, "user", None)
    if not session or not user:
        raise AuthError("Invalid email or password", 401)
    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "expires_at": session.expires_at,
        "user": {"id": user.id, "email": user.email},
    }
