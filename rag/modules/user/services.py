from abc import ABC, abstractmethod
from auth.middleware import require_auth
from supabase import Client
from typing import cast, Any, List
from constants import StudentDataModel

@abstractmethod
class User(ABC):
    def __init__(self, user_id: str, client) -> None:
        self._user_id: str = user_id
        self._client: Client  = client
        super().__init__()

    #should be implemented by the child classes
    def get_user_details(self) -> StudentDataModel:
        raise NotImplementedError("Subclasses must implement get_user_details")

def _get_data_from_supabase_where(select, where, table, client:Client ):
    try:

        if len(where) != 1:
            raise ValueError("This helper only supports a single 'eq' condition.")

        if type(select) != List or type(select) != List:
            raise ValueError("This helper expects lists for select and where.")

        record = (client.table(table).select(*select).eq(*where).single().execute())

        if record.data is None:
            raise ValueError("Could not get record from supabase")

        record_data  = cast(dict[str, Any], record.data)

        return record_data

    except Exception as e:
        raise ValueError(f"Failed to fetch record from Supabase: {str(e)}") from e


class Student(User):
    def __init__(self, user_id: str, client) -> None:
        super().__init__(user_id, client)

    def get_user_details(self) -> StudentDataModel:
        self.profile_data = {}
        try:

            student_record_data = _get_data_from_supabase_where(["id", "student_id", "registered_email", "name"], ["profile_id", str(self._user_id)], "students", self._client)


            batch_membership_record_data = _get_data_from_supabase_where(["id", "batch_id"], ["student_id", str(student_record_data["id"])], "batch_memberships", self._client)

            student_role_record_data =  _get_data_from_supabase_where(["role"], ["student_id", str(batch_membership_record_data["id"])], "student_batch_roles", self._client)

            batch_record_data = _get_data_from_supabase_where(["course_id", "batch_code", "current_semeter_id"], ["id", str(batch_membership_record_data["batch_id"])], "batches", self._client)

            semester_record_data = _get_data_from_supabase_where(["semester_number"], ["id", str(batch_membership_record_data["current_semester_id"])], "semesters", self._client)

            courses_record_data =  _get_data_from_supabase_where(["name"], ["id", str(batch_membership_record_data["course_id"])], "semesters", self._client)

            #Building the data dict

            self.profile_data = {
                **student_record_data,
                "batch_code": batch_record_data["batch_code"],
                "current_semester": semester_record_data["semester_number"],
                "course_name":  courses_record_data["name"],
                "student_role":student_role_record_data["role"]
            }

            if len(self.profile_data) <= 0:
                raise ValueError("Received Empty profile data after processing")

            return StudentDataModel.model_validate(self.profile_data)

        except Exception as e:
            raise ValueError(f"Couldn't get user details: {e}")


class Faculty(User):
    def __init__(self, user_id: str, client) -> None:
        super().__init__(user_id, client)


class Admin(User):
    def __init__(self, user_id: str, client) -> None:
        super().__init__(user_id, client)

