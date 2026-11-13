"""HTTP routes for document listing, deletion, and file access."""

import logging
from collections import Counter
from pathlib import Path
from typing import Any

from flask import Blueprint, g, jsonify, request

from config.settings import S3_BUCKET_NAME, S3_SIGNED_URL_TTL_SECONDS
from lib.aws_s3 import aws_s3_client
from lib.supabase import get_supabase_client
from modules.auth.middleware import require_auth
from s3.service import S3Service
from services.ingestion.sparse import SparseIngestion

logger = logging.getLogger(__name__)

documents = Blueprint("documents", __name__, url_prefix="/api")


def _data(response: Any) -> list[dict[str, Any]]:
    result = getattr(response, "data", response)
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        return [result]
    return []


def _document_info(
    document: dict[str, Any], chunk_counts: Counter[str]
) -> dict[str, Any]:
    document_id = str(document.get("id") or document.get("document_id"))
    title = document.get("title") or document.get("filename") or "Untitled document"
    return {
        "doc_id": document_id,
        "filename": title,
        "filetype": Path(title).suffix.lower().lstrip("."),
        "num_chunks": chunk_counts[document_id],
        "uploaded_at": document.get("created_at") or "",
        "description": document.get("description") or "",
        "document_type": document.get("document_type") or "",
        "unit": document.get("unit"),
    }


@documents.get("/documents")
@require_auth
def list_documents():
    try:
        client = get_supabase_client()
        request_body = request.get_json(silent=True) or {}
        user_batch_id = (
            request.args.get("batch_id")
            or request.args.get("batchId")
            or request_body.get("batch_id")
            or request_body.get("batchId")
        )

        if not user_batch_id and getattr(g, "current_profile", {}).get("role") == "student":
            try:
                from modules.user.services import _get_single_row_from_supabase_where

                student_record = _get_single_row_from_supabase_where(
                    ["id"],
                    ["profile_id", str(g.current_user.id)],
                    "students",
                    client=client,
                )
                if student_record and student_record.get("id"):
                    membership = _get_single_row_from_supabase_where(
                        ["batch_id"],
                        ["student_id", student_record["id"]],
                        "batch_memberships",
                        client=client,
                    )
                    if membership and membership.get("batch_id"):
                        user_batch_id = membership["batch_id"]
            except Exception as error:
                logger.warning("Could not auto-resolve batch_id for student: %s", error)

        if user_batch_id:
            doc_batches = _data(
                client.table("document_batches")
                .select("document_id")
                .eq("batch_id", user_batch_id)
                .execute()
            )
            batch_doc_ids = [
                str(row["document_id"])
                for row in doc_batches
                if row.get("document_id")
            ]

            query = client.table("documents").select(
                "id,title,s3_key,created_at,description,document_type,unit"
            )
            if batch_doc_ids:
                documents_rows = query.or_(
                    f"batch_id.eq.{user_batch_id},id.in.({','.join(batch_doc_ids)})"
                ).execute()
            else:
                documents_rows = query.eq("batch_id", user_batch_id).execute()
            document_rows = _data(documents_rows)
        else:
            document_rows = _data(
                client.table("documents")
                .select("id,title,s3_key,created_at,description,document_type,unit")
                .execute()
            )

        chunks = _data(client.table("document_chunks").select("document_id").execute())
        counts = Counter(str(chunk["document_id"]) for chunk in chunks)
        return jsonify([_document_info(document, counts) for document in document_rows])
    except Exception as error:
        logger.error("Error fetching documents: %s", error)
        return jsonify({"detail": "Could not load documents."}), 500


@documents.delete("/documents/<document_id>")
def delete_document(document_id: str):
    try:
        client = get_supabase_client()
        document_rows = _data(
            client.table("documents").select("s3_key").eq("id", document_id).execute()
        )
        client.table("document_chunks").delete().eq("document_id", document_id).execute()
        client.table("documents").delete().eq("id", document_id).execute()
        if document_rows and document_rows[0].get("s3_key") and S3_BUCKET_NAME:
            aws_s3_client.delete_object(
                Bucket=S3_BUCKET_NAME,
                Key=document_rows[0]["s3_key"],
            )
        try:
            SparseIngestion().regenerate_index()
        except Exception as sparse_error:
            logger.warning("Sparse index regeneration failed after delete: %s", sparse_error)
        return "", 204
    except Exception:
        return jsonify({"detail": "Could not delete document."}), 500


@documents.get("/documents/<document_id>/file")
@require_auth
def get_document_file(document_id: str):
    """Generate a presigned download/view URL for a document's S3 object."""
    try:
        client = get_supabase_client()
        rows = _data(
            client.table("documents")
            .select("id, title, s3_key")
            .eq("id", document_id)
            .execute()
        )
        if not rows or not rows[0].get("s3_key"):
            return jsonify({"detail": "Document not found or has no file attached"}), 404

        document = rows[0]
        filename = document.get("title") or "document"
        download_requested = request.args.get("download", "").lower() in (
            "true",
            "1",
            "yes",
        )
        presigned_url = S3Service().generate_presigned_url(
            document["s3_key"],
            filename=filename,
            download=download_requested,
        )
        if not presigned_url:
            return jsonify({"detail": "Unable to generate file download URL"}), 500

        return jsonify(
            {
                "url": presigned_url,
                "expires_in": S3_SIGNED_URL_TTL_SECONDS,
                "filename": filename,
            }
        ), 200
    except Exception as error:
        return jsonify({"detail": f"Failed to retrieve file URL: {error}"}), 500
