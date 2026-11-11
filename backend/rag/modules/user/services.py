from abc import ABC, abstractmethod
from supabase import Client
from typing import cast, Any
from .respository import _get_single_row_from_supabase_where
from .constants import StudentDataModel, FacultyDataModel, AdminDataModel

@abstractmethod
class User(ABC):
    def __init__(self, user_id: str, client) -> None:
        self._user_id: str = user_id
        self._client: Client  = client
        super().__init__()

    #should be implemented by the child classes
    def get_user_details(self) -> StudentDataModel | FacultyDataModel | AdminDataModel:
        raise NotImplementedError("Subclasses must implement get_user_details")


class Student(User):

    def __init__(self, user_id: str, client) -> None:
        super().__init__(user_id, client)

    def get_user_details(self) -> StudentDataModel:
        self.profile_data = {}
        try:

            student_record_data = _get_single_row_from_supabase_where(["id", "student_id", "official_email", "name"], ["profile_id", str(self._user_id)], "students", self._client)
            student_record_data["registered_email"] = student_record_data.get("official_email", "")

            batch_membership_record_data = _get_single_row_from_supabase_where(["id", "batch_id",], ["student_id", student_record_data["id"]], "batch_memberships", self._client)

            student_role_record_data =  _get_single_row_from_supabase_where(["role"], ["batch_membership_id", str(batch_membership_record_data["id"])], "student_batch_roles", self._client)

            batch_record_data = _get_single_row_from_supabase_where(["course_id", "batch_code", "current_semester_id"], ["id", str(batch_membership_record_data["batch_id"])], "batches", self._client)

            semester_record_data = _get_single_row_from_supabase_where(["semester_number"], ["id", str(batch_record_data["current_semester_id"])], "semesters", self._client)

            courses_record_data =  _get_single_row_from_supabase_where(["name"], ["id", str(batch_record_data["course_id"])], "courses", self._client)

            #Building the data dict
            subjects_record = (self._client.table("subjects").select("id", "subject_code", "name").eq("semester_id",str(batch_record_data["current_semester_id"])).execute())

            subjects_record_data = subjects_record.data

            if not subjects_record_data:
                raise ValueError("Couldn't get subjects")

            subjects_record_data=cast(dict[str, Any], subjects_record_data)

            self.profile_data = {
                **student_record_data,
                "batch_id": batch_membership_record_data["batch_id"],
                "batch_code": batch_record_data["batch_code"],
                "current_semester": semester_record_data["semester_number"],
                "course_name":  courses_record_data["name"],
                "student_role":student_role_record_data["role"],
                "subjects": subjects_record_data
            }

            print(self.profile_data)

            if len(self.profile_data) <= 0:
                raise ValueError("Received Empty profile data after processing")

            return StudentDataModel.model_validate(self.profile_data)

        except Exception as e:
            raise ValueError(f"Couldn't get user details: {e}")


def get_faculty_courses(supabase, faculty_id) -> FacultyDataModel:
    response = (
        supabase
        .table("faculty_assignments")
        .select("""
            batch_id,
            subject_id,
            batches (
                id,
                batch_code,
                course_id,
                courses (
                    id,
                    name,
                    code
                )
            ),
            subjects (
                id,
                name,
                subject_code,
                semester_id
            )
        """)
        .eq("faculty_id", faculty_id)
        .execute()
    )

    assignments = response.data

    courses = {}

    for assignment in assignments:
        batch = assignment["batches"]
        subject = assignment["subjects"]
        course = batch["courses"]

        course_id = course["id"]
        batch_id = batch["id"]

        # Create course
        if course_id not in courses:
            courses[course_id] = {
                "id": course_id,
                "name": course["name"],
                "code": course["code"],
                "batches": {}
            }

        # Create batch inside course
        if batch_id not in courses[course_id]["batches"]:
            courses[course_id]["batches"][batch_id] = {
                "id": batch_id,
                "batch_code": batch["batch_code"],
                "subjects": []
            }

        # Add subject taught by this faculty
        courses[course_id]["batches"][batch_id]["subjects"].append({
            "id": subject["id"],
            "name": subject["name"],
            "subject_code": subject["subject_code"]
        })

    # Convert dictionaries → lists
    result = []

    for course in courses.values():
        course["batches"] = list(course["batches"].values())
        result.append(course)

    return FacultyDataModel(courses=result)


class Faculty(User):
    def __init__(self, user_id: str, client) -> None:
        super().__init__(user_id, client)

    def get_user_details(self) -> FacultyDataModel:
        self.profile_data: FacultyDataModel|None = None
        try:
            faculty_id = _get_single_row_from_supabase_where(["id"], ["profile_id", self._user_id], "faculty", self._client)

            self.profile_data = get_faculty_courses(self._client, faculty_id=faculty_id)

            if not self.profile_data:
                raise ValueError("profile data is possible None")
            return self.profile_data

        except Exception as e:
            raise ValueError(f"User data couldn't be fetched! {e}")


class Admin(User):
    def __init__(self, user_id: str, client) -> None:
        super().__init__(user_id, client)
