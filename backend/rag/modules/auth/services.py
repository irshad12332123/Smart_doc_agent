"""Server-side auth workflow. This module never stores or logs passwords."""

from typing import Any

from lib.supabase import get_supabase_admin_client, get_supabase_client

from .constants import REGISTRY_CONFIG, GlobalRole, RegistryType
from .errors import AuthError
from .tokens import create_registration_token, read_registration_token


def _rows(response: Any) -> list[dict[str, Any]]:
    data = getattr(response, "data", response)
    return data if isinstance(data, list) else ([] if data is None else [data])


def _get_auth_user_by_email(email: str) -> Any | None:
    """Find a Supabase auth user by email via admin API."""
    try:
        admin = get_supabase_admin_client()
        users_resp = admin.auth.admin.list_users()
        users = getattr(users_resp, "users", users_resp)
        target = email.strip().lower()
        for user in users:
            if getattr(user, "email", "").strip().lower() == target:
                return user
    except Exception:
        pass
    return None


def _find_in_registry(
    email: str,
    registry_type: RegistryType | None = None,
) -> tuple[dict[str, Any] | None, RegistryType | None]:
    """Search for an official email in the configured registry tables."""
    target_email = email.strip().lower()
    types_to_check = (
        [registry_type]
        if registry_type is not None
        else [RegistryType.STUDENT, RegistryType.FACULTY]
    )

    admin = get_supabase_admin_client()
    for reg_type in types_to_check:
        config = REGISTRY_CONFIG[reg_type]
        table = config["table"]
        columns = config.get("email_columns", ["official_email", "registered_email"])
        for col in columns:
            try:
                response = (
                    admin.table(table)
                    .select(f"id, name, {col}, profile_id")
                    .ilike(col, target_email)
                    .limit(1)
                    .execute()
                )
                rows = _rows(response)
                if rows:
                    record = rows[0]
                    record["email"] = record.get(col)
                    return record, reg_type
            except Exception:
                continue

    return None, None


def check_registry(
    email: str,
    registry_type: RegistryType | None = None,
    action: str | None = None,
) -> dict[str, Any]:
    """Check email eligibility for login or registration.

    For login:
      - Check if exists in DB for that registry.
      - Check if already registered.
      - If yes, proceed; else report 'Account is not registered. Please register.'

    For register:
      - Check if exists in DB and not registered before.
      - If yes, proceed with password creation.
      - If no, report 'Either user doesn't exist or already registered.'
    """
    record, matched_type = _find_in_registry(email, registry_type)

    if not record:
        if action == "login":
            raise AuthError("Account is not registered. Please register.", 404)
        # For register or default:
        raise AuthError("Either user doesn't exist or already registered.", 404)

    is_registered = bool(record.get("profile_id"))

    if not is_registered:
        auth_user = _get_auth_user_by_email(record["email"])
        if auth_user:
            is_registered = True

    if action == "register":
        if is_registered:
            raise AuthError("Either user doesn't exist or already registered.", 409)
        return {
            "status": "eligible",
            "name": record["name"],
            "email": record["email"],
            "role": matched_type.value if matched_type else "student",
            "registration_token": create_registration_token(
                matched_type.value if matched_type else "student",
                record["email"],
            ),
        }

    if action == "login":
        if not is_registered:
            raise AuthError("Account is not registered. Please register.", 400)
        return {
            "status": "registered",
            "name": record["name"],
            "email": record["email"],
            "role": matched_type.value if matched_type else "student",
        }

    # Default without explicit action parameter:
    if is_registered:
        return {
            "status": "already registered",
            "message": "You already have an account.",
            "name": record["name"],
            "email": record["email"],
            "role": matched_type.value if matched_type else "student",
        }

    return {
        "status": "eligible",
        "name": record["name"],
        "email": record["email"],
        "role": matched_type.value if matched_type else "student",
        "registration_token": create_registration_token(
            matched_type.value if matched_type else "student",
            record["email"],
        ),
    }


def register_account(
    raw_password: str,
    registration_token: str | None = None,
    email: str | None = None,
    registry_type: RegistryType | None = None,
) -> dict[str, str]:
    """Register an account using Supabase Auth with email confirmation required."""
    target_email: str | None = None
    target_registry_type: RegistryType | None = registry_type

    if registration_token:
        token = read_registration_token(registration_token)
        try:
            target_registry_type = RegistryType(token["type"])
        except (KeyError, ValueError) as error:
            raise AuthError("Registration session is invalid", 401) from error
        target_email = token.get("email") or token.get("registry_id")
    elif email:
        target_email = email.strip().lower()

    if not target_email:
        raise AuthError("Email or registration session is required", 400)

    record, matched_type = _find_in_registry(target_email, target_registry_type)
    if not record or not matched_type:
        raise AuthError("Either user doesn't exist or already registered.", 404)
    if record.get("profile_id"):
        raise AuthError("Either user doesn't exist or already registered.", 409)

    admin = get_supabase_admin_client()
    client = get_supabase_client()

    # Check if user already exists in auth.users
    existing_user = _get_auth_user_by_email(record["email"])
    if existing_user:
        confirmed = getattr(existing_user, "email_confirmed_at", None) or getattr(
            existing_user, "confirmed_at", None
        )
        if confirmed:
            raise AuthError("Either user doesn't exist or already registered.", 409)
        # User started registration earlier but did not confirm. Delete old unconfirmed entry so fresh signup sends email.
        try:
            admin.auth.admin.delete_user(existing_user.id)
        except Exception:
            pass

    created_user_id: str | None = None
    try:
        # Use client sign_up so Supabase automatically generates and delivers the confirmation email
        signup_resp = client.auth.sign_up(
            {
                "email": record["email"],
                "password": raw_password,
                "options": {
                    "data": {
                        "full_name": record["name"],
                        "role": matched_type.value,
                    }
                },
            }
        )

        user = getattr(signup_resp, "user", None)
        created_user_id = getattr(user, "id", None)
        if not created_user_id:
            raise RuntimeError("Supabase did not return a new user id")

        # Check if identities list is empty (indicates already registered in GoTrue)
        identities = getattr(user, "identities", None)
        if identities is not None and len(identities) == 0:
            raise AuthError("Either user doesn't exist or already registered.", 409)

        config = REGISTRY_CONFIG[matched_type]
        # SQL RPC locks the registry row and creates the profile & foreign key link
        admin.rpc(
            "complete_registry_registration",
            {
                "p_registry_type": matched_type.value,
                "p_registry_id": record["id"],
                "p_profile_id": created_user_id,
                "p_full_name": record["name"],
                "p_role": config["role"].value,
            },
        ).execute()

    except AuthError:
        if created_user_id:
            try:
                admin.auth.admin.delete_user(created_user_id)
            except Exception:
                pass
        raise
    except Exception as error:
        if created_user_id:
            try:
                admin.auth.admin.delete_user(created_user_id)
            except Exception:
                pass
        message = str(error).lower()
        if "already" in message or "duplicate" in message:
            raise AuthError("Either user doesn't exist or already registered.", 409) from error
        if "rate limit" in message:
            raise AuthError("Email rate limit exceeded. Please wait a few minutes before trying again.", 429) from error
        raise AuthError(f"Unable to create account: {str(error)}", 502) from error

    return {
        "status": "pending_confirmation",
        "message": "Registration successful! A confirmation email has been sent by Supabase. Please verify your email before logging in.",
        "email": record["email"],
    }


def sign_in(
    email: str,
    raw_password: str,
    registry_type: RegistryType | None = None,
) -> dict[str, Any]:
    """Authenticate user with password after verifying registry presence and registration."""
    target_email = email.strip().lower()
    admin = get_supabase_admin_client()
    profile_summary: dict[str, Any] | None = None

    record, matched_type = _find_in_registry(target_email, registry_type)

    if not record:
        # Check if account belongs to platform admin
        auth_user = _get_auth_user_by_email(target_email)
        if auth_user:
            prof = (
                admin.table("profiles")
                .select("id, full_name, role")
                .eq("id", auth_user.id)
                .limit(1)
                .execute()
            )
            rows = _rows(prof)
            if not rows or rows[0].get("role") != GlobalRole.ADMIN.value:
                raise AuthError("Account is not registered. Please register.", 404)
            profile_summary = {
                "id": rows[0]["id"],
                "full_name": rows[0].get("full_name") or "Administrator",
                "role": rows[0]["role"],
            }
        else:
            raise AuthError("Account is not registered. Please register.", 404)
    else:
        # Registry record found: must already be registered with a linked profile or auth user
        if not record.get("profile_id"):
            auth_user = _get_auth_user_by_email(record["email"])
            if not auth_user:
                raise AuthError("Account is not registered. Please register.", 400)
        profile_summary = {
            "id": record.get("profile_id") or "",
            "full_name": record.get("name") or "",
            "role": matched_type.value if matched_type else "",
        }

    try:
        response = get_supabase_client().auth.sign_in_with_password(
            {"email": target_email, "password": raw_password}
        )
    except Exception as error:
        err_msg = str(error).lower()
        if "email not confirmed" in err_msg or "not confirmed" in err_msg:
            raise AuthError(
                "Please confirm your email before signing in. Check your inbox for the confirmation link.",
                403,
            ) from error
        if "invalid" in err_msg or "credentials" in err_msg:
            raise AuthError("Invalid email or password", 401) from error
        raise AuthError("Invalid email or password", 401) from error

    session = getattr(response, "session", None)
    user = getattr(response, "user", None)
    if not session or not user:
        raise AuthError("Invalid email or password", 401)

    # Ensure profile linking if it was deferred or unlinked
    if record and not record.get("profile_id") and matched_type:
        try:
            config = REGISTRY_CONFIG[matched_type]
            admin.rpc(
                "complete_registry_registration",
                {
                    "p_registry_type": matched_type.value,
                    "p_registry_id": record["id"],
                    "p_profile_id": user.id,
                    "p_full_name": record["name"],
                    "p_role": config["role"].value,
                },
            ).execute()
        except Exception:
            pass

    if profile_summary is None:
        raise AuthError("User profile is not configured", 401)
    profile_summary["id"] = user.id

    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "expires_at": session.expires_at,
        "user": {"id": user.id, "email": user.email},
        "profile_summary": profile_summary,
    }


def resend_confirmation_email(email: str) -> dict[str, str]:
    """Resend Supabase signup confirmation email."""
    target_email = email.strip().lower()
    try:
        get_supabase_client().auth.resend({"type": "signup", "email": target_email})
    except Exception as error:
        raise AuthError(f"Could not resend confirmation email: {str(error)}", 400) from error
    return {"message": "Confirmation email resent successfully."}
