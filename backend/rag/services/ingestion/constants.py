import re
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class DocumentMetaData(BaseModel):
    model_config = ConfigDict(extra="allow")

    description: str = Field(..., description="Summary of the document content")
    deadline: Optional[str] = Field(None, description="Deadline if mentioned, YYYY-MM-DD or ISO")
    document_type: Literal["notice", "assignment", "syllabus", "notes", "time_table", "others"] = Field(...)
    unit: Optional[int] = Field(
        None,
        description="Academic unit or module number if covered in document, e.g. 1, 2, 3",
    )

    @field_validator("unit", mode="before")
    @classmethod
    def parse_unit(cls, v: Any) -> Optional[int]:
        if v is None:
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            v_clean = v.strip()
            if not v_clean or v_clean.lower() in ("null", "none", "n/a", "na", ""):
                return None
            match = re.search(r"\b\d+\b", v_clean)
            if match:
                return int(match.group(0))
        return None


class DocumentIdMetaData(BaseModel):
    subject_id: str = Field(...)
