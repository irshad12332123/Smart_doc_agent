from pydantic import BaseModel, Field
from typing import Literal, Optional

class DocumentMetaData(BaseModel):
    description: str = Field(...)
    deadline: Optional[str] = None
    document_type: Literal["notice", "assignment", "syllabus", "notes", "time_table", "others"]

class DocumentIdMetaData(BaseModel):
    subject_id: str = Field(...)
