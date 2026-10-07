from typing import Literal, Optional
from pydantic import BaseModel, Field, ConfigDict

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
    model_config = ConfigDict(extra="ignore")

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
    search_query: Optional[str] = Field(
        None,
        description="Extracted keywords, assignment number, or title keywords for metadata lookup, or null for general listings",
    )
    deadline_filter: Optional[DeadlineFilter] = None
    time_filter: Optional[TimeFilter] = None
    limit: int = Field(20, description="Maximum number of documents to retrieve")
