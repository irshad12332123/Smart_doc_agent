from flask import request, jsonify, Blueprint
from modules.auth.middleware import require_auth
from lib.supabase import get_supabase_client
from modules.user.services import Student, Faculty
from modules.user.constants import StudentDataModel , FacultyDataModel, AdminDataModel
user = Blueprint("user", __name__, url_prefix="/u")

def _body() -> dict:

    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        raise ValueError("A JSON request body is required")
    return payload

@user.get("/profile")
@require_auth
def profile():

    profile_data: StudentDataModel | FacultyDataModel | AdminDataModel | None = None
    try:

        from flask import g
        user_role = g.current_profile.get("role")

        if user_role not in ["admin", "student", "faculty"]:
            return jsonify({"message": "we don't except this role"}), 403

        if user_role == "student":
            student = Student(g.current_user.id, client=get_supabase_client())
            profile_data  = student.get_user_details()

        elif user_role ==  "faculty":
            faculty = Faculty(g.current_user.id, client=get_supabase_client())
            profile_data = faculty.get_user_details()

        if not profile_data:
                raise ValueError("Couldn't get profile, from route")

        return jsonify({"data": profile_data.model_dump()}), 200

    except:
        raise ValueError("Error")
