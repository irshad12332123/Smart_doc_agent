import logging
from typing import Any, Optional

from supabase import Client

from lib.supabase import get_supabase_client

logger = logging.getLogger(__name__)


def _extract_data(response: Any) -> list[dict[str, Any]]:
    result = getattr(response, "data", response)
    if isinstance(result, list):
        return result
    elif isinstance(result, dict):
        return [result]
    return []


class DocumentRepository:
    """
    Deterministic Document Repository.
    Executes filtered queries against Supabase via the get_documents_by_filters RPC,
    with an automatic fallback to direct table querying if the RPC is unavailable.
    """

    def __init__(self, client: Optional[Client] = None):
        self._client = client

    def _get_client(self) -> Client:
        if self._client is not None:
            return self._client
        return get_supabase_client()

    def get_documents_by_filters(
        self,
        subject_id: Optional[str] = None,
        document_type: Optional[str] = None,
        search_query: Optional[str] = None,
        deadline_start: Optional[str] = None,
        deadline_end: Optional[str] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Retrieves document metadata from Supabase matching exact metadata filters
        and keyword/title search queries.
        """
        client = self._get_client()

        # Build RPC params
        rpc_params: dict[str, Any] = {
            "p_subject_id": subject_id,
            "p_document_type": document_type,
            "p_search_query": search_query,
            "p_deadline_start": deadline_start,
            "p_deadline_end": deadline_end,
            "p_created_after": created_after,
            "p_created_before": created_before,
            "p_limit": limit,
        }

        # Clean out None keys for cleaner payload if preferred
        cleaned_params = {k: v for k, v in rpc_params.items() if v is not None}

        try:
            rpc_res = client.rpc("get_documents_by_filters", cleaned_params).execute()
            rows = _extract_data(rpc_res)
            if rows is not None:
                return rows
        except Exception as rpc_err:
            logger.warning(
                f"RPC 'get_documents_by_filters' failed ({rpc_err}). Falling back to table query."
            )

        # Fallback to direct table query
        try:
            query = client.table("documents").select(
                "id, title, description, document_type, subject_id, uploaded_by, s3_key, mime_type, deadline, created_at, updated_at, subjects(name, subject_code)"
            )

            if subject_id:
                query = query.eq("subject_id", subject_id)
            if document_type:
                query = query.ilike("document_type", f"%{document_type}%")
            if deadline_start:
                query = query.gte("deadline", deadline_start)
            if deadline_end:
                query = query.lte("deadline", deadline_end)
            if created_after:
                query = query.gte("created_at", created_after)
            if created_before:
                query = query.lte("created_at", created_before)
            if search_query and search_query.strip():
                # Title or description match
                sq = search_query.strip()
                query = query.or_(f"title.ilike.%{sq}%,description.ilike.%{sq}%")

            query = query.order("created_at", desc=True).limit(limit)
            res = query.execute()
            raw_rows = _extract_data(res)

            # Flatten subject relation if returned from table join
            flattened_rows: list[dict[str, Any]] = []
            for r in raw_rows:
                row_copy = dict(r)
                subj = row_copy.pop("subjects", None)
                if isinstance(subj, dict):
                    row_copy["subject_name"] = subj.get("name")
                    row_copy["subject_code"] = subj.get("subject_code") or subj.get("code")
                flattened_rows.append(row_copy)

            return flattened_rows

        except Exception as table_err:
            logger.error(f"Fallback table query failed: {table_err}")
            return []
