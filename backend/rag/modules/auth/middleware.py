from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import g, request

from lib.supabase import get_supabase_client

from .constants import GlobalRole, StudentRole
from .errors import AuthError
from rag.modules.user.services import _get_single_row_from_supabase_where

def require_auth(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any):
        header = request.headers.get("Authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise AuthError("A bearer access token is required", 401)
        try:
            user_response = get_supabase_client().auth.get_user(token)
            user = getattr(user_response, "user", None)
            if not user:
                raise ValueError("No authenticated user")
            profile_response = (
                get_supabase_client().table("profiles").select("id, full_name, role").eq("id", user.id).single().execute()
            )

            """
            attach the batches, courses, id, email,
            """

            profile = getattr(profile_response, "data", None)
            # print(profile)
            if not profile:
                raise ValueError("No profile")
        except Exception as error:
            raise AuthError("Invalid or expired access token", 401) from error
        g.current_user = user
        g.current_profile = profile
        return view(*args, **kwargs)
    return wrapped


def require_role(*roles: GlobalRole | StudentRole) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(view: Callable[..., Any]) -> Callable[..., Any]:
        @require_auth
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any):
            role: str= g.current_profile.get("role")
            if role == "student":
                # if Student role is not CR reject
                # get Student role
                student_record_data = _get_single_row_from_supabase_where(["id"], ["profile_id", str(g.current_user.id)], "students", client=get_supabase_client())

                batch_membership_record_data = _get_single_row_from_supabase_where(["id",], ["student_id", student_record_data["id"]], "batch_memberships", client=get_supabase_client())

                student_role_record_data =  _get_single_row_from_supabase_where(["role"], ["batch_membership_id", str(batch_membership_record_data["id"])], "student_batch_roles", client=get_supabase_client())

                role = student_role_record_data["role"]
            if role not in {role.value for role in roles}:
                raise AuthError("You do not have permission to perform this action", 403)
            return view(*args, **kwargs)
        return wrapped
    return decorator
