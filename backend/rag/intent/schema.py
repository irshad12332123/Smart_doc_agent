import re
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

IntentType = Literal["document_listing", "document_search", "normal_rag_query"]

DocumentType = Literal[
    "assignment",
    "notice",
    "study_material",
    "notes",
    "announcement",
    "syllabus",
    "time_table",
    "other",
    "others",
]

DeadlineFilterType = Literal["before", "after", "between"]

TimeFilterType = Literal[
    "today",
    "yesterday",
    "last_7_days",
    "this_week",
    "next_week",
    "this_month",
]


class SubjectContext(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    code: Optional[str] = None
    subject_code: Optional[str] = None


class DeadlineFilter(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Optional[DeadlineFilterType] = None
    start: Optional[str] = None
    end: Optional[str] = None


class TimeFilter(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Optional[TimeFilterType] = None
    start: Optional[str] = None
    end: Optional[str] = None


class DocumentIntent(BaseModel):
    model_config = ConfigDict(extra="allow")

    intent: IntentType = Field(
        ...,
        description="Structured classification of the query intent: document_listing, document_search, or normal_rag_query",
    )
    document_type: Optional[DocumentType] = Field(
        None,
        description="Target document type if explicitly or implicitly requested, otherwise null",
    )
    subject_id: Optional[str] = Field(
        None,
        description="UUID of the matched subject strictly from the user's available subjects list, otherwise null",
    )
    unit: Optional[int] = Field(
        None,
        description="Academic unit or module number (e.g. 1, 2, 3) for unit-level document filtering, otherwise null",
    )
    search_query: Optional[str] = Field(
        None,
        description="Optional legacy/fallback keywords if searching non-unit terms, otherwise null",
    )
    deadline_filter: Optional[DeadlineFilter] = None
    time_filter: Optional[TimeFilter] = None
    limit: int = Field(20, description="Maximum number of documents to retrieve")
    metadata_filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible key-value pairs for additional/future metadata column filters",
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
