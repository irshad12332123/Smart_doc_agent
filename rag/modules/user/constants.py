from pydantic import BaseModel
from typing import Iterable

class StudentDataModel(BaseModel):
    id: str
    student_id: str
    registered_email: str
    name: str
    batch_code: str
    current_semester: int
    course_name: str
    student_role: str


class FacultyDataModel(BaseModel):
    id: str
    faculty_id: str
    registered_email: str
    name: str
    current_semester: int
    courses: Iterable
    faculty_role: str
    subjects: Iterable

class AdminDataModel(BaseModel):
    pass
