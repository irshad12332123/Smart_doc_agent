import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence

from groq import Groq

try:
    from config.settings import GROQ_MODEL
    from language_models.sml import load_slm
except ImportError:
    from rag.config.settings import GROQ_MODEL
    from rag.language_models.sml import load_slm
from .prompt import get_intent_extraction_prompt
from .schema import (
    DeadlineFilter,
    DocumentIntent,
    DocumentType,
    SubjectContext,
    TimeFilter,
)

logger = logging.getLogger(__name__)

VALID_DOCUMENT_TYPES: set[str] = {
    "assignment",
    "notice",
    "study_material",
    "notes",
    "announcement",
    "syllabus",
    "time_table",
    "other",
    "others",
}

DOCUMENT_TYPE_ALIASES: dict[str, DocumentType] = {
    "assignments": "assignment",
    "homework": "assignment",
    "lab": "assignment",
    "notices": "notice",
    "circular": "notice",
    "circulars": "notice",
    "announcements": "announcement",
    "lecture_notes": "notes",
    "lecture": "notes",
    "slides": "notes",
    "timetable": "time_table",
    "schedule": "time_table",
    "other": "other",
    "others": "others",
}


class IntentExtractor:
    """
    Extracts strongly typed document intents from natural language queries
    using the project's SLM, with strict client-side validation against
    the user's authorized subject context and schema definitions.
    """

    def __init__(self, client: Optional[Groq] = None, model: str = GROQ_MODEL):
        self._client = client
        self._model = model

    def _get_client(self) -> Optional[Groq]:
        if self._client is not None:
            return self._client
        try:
            return load_slm()
        except Exception as e:
            logger.warning(f"Could not initialize Groq SLM client: {e}")
            return None

    @staticmethod
    def normalize_subjects(
        raw_subjects: Sequence[Any] | None,
    ) -> list[SubjectContext]:
        """
        Normalizes a heterogeneous list of subject objects, dictionaries,
        or strings into strongly typed SubjectContext models.
        """
        if not raw_subjects:
            return []

        normalized: list[SubjectContext] = []
        for item in raw_subjects:
            if isinstance(item, SubjectContext):
                normalized.append(item)
            elif isinstance(item, dict):
                sub_id = str(item.get("id") or "").strip()
                name = str(item.get("name") or item.get("title") or "").strip()
                code = item.get("code") or item.get("subject_code")
                if sub_id and name:
                    normalized.append(
                        SubjectContext(
                            id=sub_id,
                            name=name,
                            code=str(code).strip() if code else None,
                        )
                    )
            elif isinstance(item, str) and item.strip():
                # If only string name provided without explicit UUID
                normalized.append(
                    SubjectContext(
                        id=item.strip().lower(),
                        name=item.strip(),
                        code=None,
                    )
                )
        return normalized

    @staticmethod
    def compute_time_range(
        time_filter_type: Optional[str],
        reference_time: datetime,
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Computes UTC ISO start and end timestamps for relative time filters.
        """
        if not time_filter_type:
            return None, None

        ref = reference_time.astimezone(timezone.utc)
        filter_lower = time_filter_type.lower()

        if filter_lower == "today":
            start = ref.replace(hour=0, minute=0, second=0, microsecond=0)
            end = ref.replace(hour=23, minute=59, second=59, microsecond=999999)
            return start.isoformat(), end.isoformat()

        elif filter_lower == "yesterday":
            yesterday = ref - timedelta(days=1)
            start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
            return start.isoformat(), end.isoformat()

        elif filter_lower == "last_7_days":
            start = ref - timedelta(days=7)
            return start.isoformat(), ref.isoformat()

        elif filter_lower == "this_week":
            # Monday of current week
            start = (ref - timedelta(days=ref.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            end = (start + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)
            return start.isoformat(), end.isoformat()

        elif filter_lower == "next_week":
            # Monday of next week
            start = (ref + timedelta(days=7 - ref.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            end = (start + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)
            return start.isoformat(), end.isoformat()

        elif filter_lower == "this_month":
            start = ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Calculate end of month
            next_month = ref.replace(day=28) + timedelta(days=4)
            end = (next_month - timedelta(days=next_month.day)).replace(hour=23, minute=59, second=59, microsecond=999999)
            return start.isoformat(), end.isoformat()

        return None, None

    def extract(
        self,
        query: str,
        subject_list: Sequence[Any] | None = None,
        reference_time: Optional[datetime] = None,
    ) -> DocumentIntent:
        """
        Parses a query into a validated DocumentIntent model.
        Falls back safely to normal_rag_query if SLM or parsing fails.
        """
        if not query or not query.strip():
            return DocumentIntent(intent="normal_rag_query")

        ref_time = reference_time or datetime.now(timezone.utc)
        normalized_subjects = self.normalize_subjects(subject_list)
        valid_subject_ids = {s.id for s in normalized_subjects}

        client = self._get_client()
        if client is None:
            logger.warning("SLM client unavailable, falling back to normal_rag_query")
            return DocumentIntent(intent="normal_rag_query")

        prompt = get_intent_extraction_prompt(
            query=query.strip(),
            subjects=normalized_subjects,
            current_time_iso=ref_time.isoformat(),
        )

        try:
            response = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise academic intent extractor. Respond strictly with valid JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                model=self._model,
                temperature=0.0,
                max_tokens=1000,
                response_format={"type": "json_object"},
            )

            raw_text = response.choices[0].message.content or "{}"
            parsed = json.loads(raw_text)

        except Exception as e:
            logger.warning(f"Failed to extract intent via SLM: {e}. Falling back to normal RAG.")
            return DocumentIntent(intent="normal_rag_query")

        return self.validate_and_sanitize(parsed, valid_subject_ids, ref_time)

    def validate_and_sanitize(
        self,
        raw_intent: dict[str, Any],
        valid_subject_ids: set[str],
        reference_time: datetime,
    ) -> DocumentIntent:
        """
        Validates every field from the SLM against authorized subject IDs,
        valid document types, and computes temporal boundaries.
        """
        intent_type = raw_intent.get("intent")
        if intent_type not in {"document_listing", "document_search", "normal_rag_query"}:
            intent_type = "normal_rag_query"

        # Validate subject_id
        raw_subject_id = raw_intent.get("subject_id")
        subject_id: Optional[str] = None
        if raw_subject_id and str(raw_subject_id) in valid_subject_ids:
            subject_id = str(raw_subject_id)
        elif raw_subject_id:
            # If SLM hallucinated or returned an unknown subject ID, discard it
            logger.warning(f"Discarding invalid/unauthorized subject_id: {raw_subject_id}")
            subject_id = None

        # Validate document_type
        raw_doc_type = raw_intent.get("document_type")
        document_type: Optional[DocumentType] = None
        if raw_doc_type and isinstance(raw_doc_type, str):
            doc_key = raw_doc_type.lower().strip()
            if doc_key in VALID_DOCUMENT_TYPES:
                document_type = doc_key  # type: ignore
            elif doc_key in DOCUMENT_TYPE_ALIASES:
                document_type = DOCUMENT_TYPE_ALIASES[doc_key]

        # Validate search_query
        search_query_raw = raw_intent.get("search_query")
        search_query: Optional[str] = None
        if search_query_raw and isinstance(search_query_raw, str) and search_query_raw.strip():
            search_query = search_query_raw.strip()
            if search_query.lower() in {"null", "none", ""}:
                search_query = None

        # Handle deadline_filter
        deadline_filter_obj: Optional[DeadlineFilter] = None
        raw_deadline = raw_intent.get("deadline_filter")
        if isinstance(raw_deadline, dict):
            d_type = raw_deadline.get("type")
            d_start = raw_deadline.get("start")
            d_end = raw_deadline.get("end")
            if d_type in {"before", "after", "between"}:
                deadline_filter_obj = DeadlineFilter(
                    type=d_type,
                    start=str(d_start) if d_start else None,
                    end=str(d_end) if d_end else None,
                )

        # Handle time_filter
        time_filter_obj: Optional[TimeFilter] = None
        raw_time = raw_intent.get("time_filter")
        if isinstance(raw_time, dict):
            t_type = raw_time.get("type")
            if t_type:
                start_iso, end_iso = self.compute_time_range(t_type, reference_time)
                time_filter_obj = TimeFilter(
                    type=t_type if t_type in {"today", "yesterday", "last_7_days", "this_week", "next_week", "this_month"} else None,
                    start=start_iso or raw_time.get("start"),
                    end=end_iso or raw_time.get("end"),
                )

        # Limit
        limit = raw_intent.get("limit") or 20
        try:
            limit = max(1, min(int(limit), 100))
        except (ValueError, TypeError):
            limit = 20

        return DocumentIntent(
            intent=intent_type,
            document_type=document_type,
            subject_id=subject_id,
            search_query=search_query,
            deadline_filter=deadline_filter_obj,
            time_filter=time_filter_obj,
            limit=limit,
        )
