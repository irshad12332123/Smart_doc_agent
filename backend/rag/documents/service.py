import logging
from typing import Any, Optional

from intent.schema import DocumentIntent
from s3.service import S3Service
from .repository import DocumentRepository

logger = logging.getLogger(__name__)


class DocumentService:
    """
    Business service for deterministic document queries and S3 signed URL resolution.
    """

    def __init__(
        self,
        repository: Optional[DocumentRepository] = None,
        s3_service: Optional[S3Service] = None,
    ):
        self.repository = repository or DocumentRepository()
        self.s3_service = s3_service or S3Service()

    def lookup_documents(
        self,
        intent: DocumentIntent,
        generate_signed_urls: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Executes a deterministic lookup in the database based on the extracted intent,
        resolves secure presigned URLs for each document's S3 key, and formats the result.
        """
        deadline_start = None
        deadline_end = None
        if intent.deadline_filter:
            deadline_start = intent.deadline_filter.start
            deadline_end = intent.deadline_filter.end

        created_after = None
        created_before = None
        if intent.time_filter:
            created_after = intent.time_filter.start
            created_before = intent.time_filter.end

        raw_docs = self.repository.get_documents_by_filters(
            subject_id=intent.subject_id,
            document_type=intent.document_type,
            unit=getattr(intent, "unit", None),
            search_query=intent.search_query,
            deadline_start=deadline_start,
            deadline_end=deadline_end,
            created_after=created_after,
            created_before=created_before,
            limit=intent.limit,
            metadata_filters=getattr(intent, "metadata_filters", None),
        )

        processed_docs: list[dict[str, Any]] = []
        for doc in raw_docs:
            s3_key = doc.get("s3_key")
            file_url: Optional[str] = None

            if generate_signed_urls and s3_key:
                try:
                    file_url = self.s3_service.generate_presigned_url(s3_key)
                except Exception as s3_err:
                    logger.warning(
                        f"Could not generate signed URL for document {doc.get('id')} ({s3_key}): {s3_err}"
                    )
                    file_url = None

            doc_id = str(doc.get("id") or "")
            title = doc.get("title") or "Untitled Document"

            doc_dict = {
                "id": doc_id,
                "doc_id": doc_id,
                "title": title,
                "filename": title,
                "description": doc.get("description") or "",
                "document_type": doc.get("document_type") or "other",
                "unit": doc.get("unit"),
                "subject_id": str(doc.get("subject_id") or "") if doc.get("subject_id") else None,
                "subject_name": doc.get("subject_name"),
                "subject_code": doc.get("subject_code"),
                "uploaded_by": str(doc.get("uploaded_by") or "") if doc.get("uploaded_by") else None,
                "s3_key": s3_key,
                "file_url": file_url,
                "mime_type": doc.get("mime_type") or "application/octet-stream",
                "deadline": doc.get("deadline"),
                "created_at": doc.get("created_at"),
                "updated_at": doc.get("updated_at"),
            }

            # Extensible: pass through any additional/future columns in doc
            for k, v in doc.items():
                if k not in doc_dict:
                    doc_dict[k] = v

            processed_docs.append(doc_dict)

        logger.debug(f"processed_docs count: {len(processed_docs)}")
        return processed_docs
