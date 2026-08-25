from flask import request, jsonify, Blueprint
from auth.middleware import require_auth
from services import Student
from lib.supabase import get_supabase_client
from constants import StudentDataModel, FacultyDataModel, AdminDataModel

user = Blueprint("user", __name__, url_prefix="/u")


def _body() -> dict:

    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        raise ValueError("A JSON request body is required")
    return payload

@user.get("/profile")
@require_auth
def profile():
    # payload = _body()
    profile_data: StudentDataModel | FacultyDataModel | AdminDataModel | None = None
    try:

        from flask import g
        user_role = g.current_profile.get("role")

        if user_role not in ["admin", "student", "faculty"]:
            return jsonify({"message": "we don't except this role"}), 403

        if user_role is "student":
            student = Student(g.current_user.id, client=get_supabase_client())
            profile_data  = student.get_user_details()

        elif user_role is "faculty":
            pass
        
        if not profile_data:
                raise ValueError("Couldn't get profile, from route")

        return jsonify({"data": profile_data.model_dump()}), 200

    except:
        raise ValueError("Error")
