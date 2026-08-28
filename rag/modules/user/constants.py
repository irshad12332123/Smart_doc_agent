from pydantic import BaseModel
from uuid import UUID

class StudentSubjects(BaseModel):
    id: UUID
    name: str
    subject_code: str

class StudentDataModel(BaseModel):
    student_id: str
    registered_email: str
    name: str
    batch_code: str
    current_semester: int
    course_name: str
    student_role: str
    subjects: list[StudentSubjects]
    
class FacultySubject(BaseModel):
    id: UUID
    name: str
    subject_code: str


class FacultyBatch(BaseModel):
    id: UUID
    batch_code: str
    subjects: list[FacultySubject]


class FacultyCourse(BaseModel):
    id: UUID
    name: str
    code: str
    batches: list[FacultyBatch]


class FacultyDataModel(BaseModel):
    courses: list[FacultyCourse]

class AdminDataModel(BaseModel):
    pass
