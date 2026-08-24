from pydantic import BaseModel, Field
from typing import Literal, Optional

class DocumentMetaData(BaseModel):
    description: str = Field(...)
    deadline: Optional[str] = None
    needs_id_extraction: Literal["no", "yes"] = Field(...)
    document_type: Literal["notice", "assignment", "syllabus", "notes", "time_table", "other"]

class DocumentIdMetaData(BaseModel):
    batch_id: str = Field(...)
    semester_id: str = Field(...)
    uploaded_by:  Optional[str] = None
    course_id: str
    subject_id: str = Field(...)
