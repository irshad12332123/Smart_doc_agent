import json
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import  Any
from flask import Blueprint, Response, jsonify, request, stream_with_context
from groq import Groq

from services.retriever.dense import DenseRetriever
from modules.auth.middleware import require_auth
from language_models.services import CallLLM
from language_models.sml import load_slm
from config.settings import (
    S3_BUCKET_NAME,
)

from lib.aws_s3 import aws_s3_client
from lib.supabase import get_supabase_client
from services.ingestion.dense import DenseIngestion
from services.ingestion.sparse import SparseIngestion
from services.retriever.sparse import SparseRetriever
from services.retriever.hybrid import HybridRetriever

ingest = Blueprint("ingest", __name__, url_prefix="/api")

def _data(response: Any) -> list[dict[str, Any]]:
    result = getattr(response, "data", response)
    return result if isinstance(result, list) else ([] if result is None else [result])

def _required_s3_bucket() -> str:
    if not S3_BUCKET_NAME:
        raise RuntimeError("S3_BUCKET_NAME must be configured")
    return S3_BUCKET_NAME

def _document_info(document: dict[str, Any], chunk_counts: Counter[str]) -> dict[str, Any]:
    document_id = str(document.get("id") or document.get("document_id"))
    title = document.get("title") or document.get("filename") or "Untitled document"
    return {
        "doc_id": document_id,
        "filename": title,
        "filetype": Path(title).suffix.lower().lstrip("."),
        "num_chunks": chunk_counts[document_id],
        "uploaded_at": document.get("created_at") or "",
    }

@ingest.route("/ingest", methods=["POST"])
@require_auth
def ingest_files():
    print("request rceived")
    files = request.files.getlist("files")
    batch_ids = request.form.getlist("batch_ids")
    subject_id = request.form.get("subject_id") or None


    if not files:
        return jsonify({"detail": "Attach at least one file in the 'files' field."}), 400

    if not batch_ids:
        return jsonify({"detail": "At least one batch is required."}), 400

    supabase = get_supabase_client()
    del supabase

    completed: list[dict[str, Any]] = []

    try:
        bucket = _required_s3_bucket()

        #initializing the generator--
        context_meta_data_generator: Groq = load_slm()

        dense_ingester = DenseIngestion()

        for uploaded_file in files:
            completed.append(dense_ingester.ingest(uploaded_file, context_meta_data_generator, subject_id, batch_ids, aws_s3_client, bucket))

        # Regenerate the BM25 sparse index to keep local index in sync with Supabase
        try:
            SparseIngestion().regenerate_index()
        except Exception as sparse_err:
            print("Warning: Sparse index regeneration failed after upload:", sparse_err)

    except (RuntimeError, ValueError) as error:
        return jsonify({"detail": str(error)}), 400
    except Exception as e:
        return jsonify({"detail": "Document ingestion failed. Check the server logs.", "error": str(e)}), 500

    return jsonify({"documents": completed, "total_chunks_added": sum(d["num_chunks"] for d in completed)}), 201

@ingest.route("/index/sync", methods=["POST"])
def sync_index():
    """Manually trigger BM25 sparse index regeneration from Supabase."""
    try:
        metadata = SparseIngestion().regenerate_index()
        return jsonify({"status": "success", "message": "Sparse BM25 index regenerated successfully", "metadata": metadata}), 200
    except Exception as e:
        return jsonify({"detail": f"Failed to sync sparse index: {e}"}), 500

@ingest.route("/retrieve/sparse", methods=["POST"])
def retrieve_sparse():
    """Retrieve document chunks using BM25 sparse retriever."""
    payload = request.get_json(silent=True) or {}
    query = payload.get("query")
    match_count = payload.get("match_count")
    match_threshold = payload.get("match_threshold", 0.0)
    document_ids = payload.get("document_ids")

    if not query or not isinstance(query, str) or not query.strip():
        return jsonify({"detail": "Query string is required"}), 400

    try:
        retriever = SparseRetriever()
        results = retriever.retrieve(
            query=query,
            match_count=match_count,
            match_threshold=match_threshold,
            document_ids=document_ids,
        )
        return jsonify({"query": query, "results": results, "count": len(results)}), 200
    except Exception as e:
        return jsonify({"detail": f"Sparse retrieval failed: {e}"}), 500

@ingest.route("/retrieve/hybrid", methods=["POST"])
def retrieve_hybrid():
    """Retrieve document chunks using Hybrid retriever (Dense + BM25S + RRF + optional CrossEncoder)."""
    payload = request.get_json(silent=True) or {}
    query = payload.get("query")
    match_count = payload.get("match_count")
    rerank = payload.get("rerank", False)
    dense_weight = payload.get("dense_weight", 1.0)
    sparse_weight = payload.get("sparse_weight", 1.0)
    document_ids = payload.get("document_ids")

    if not query or not isinstance(query, str) or not query.strip():
        return jsonify({"detail": "Query string is required"}), 400

    try:
        retriever = HybridRetriever()
        results = retriever.retrieve(
            query=query,
            match_count=match_count,
            dense_weight=dense_weight,
            sparse_weight=sparse_weight,
            rerank=rerank,
            document_ids=document_ids,
        )
        return jsonify({
            "query": query,
            "reranked": rerank,
            "results": results,
            "count": len(results),
        }), 200
    except Exception as e:
        return jsonify({"detail": f"Hybrid retrieval failed: {e}"}), 500

@ingest.route("/evaluation/run", methods=["POST", "GET"])
def run_evaluation():
    """Run retrieval benchmark evaluation on the college dataset."""
    try:
        from evaluation.evaluator import RetrievalEvaluator
        evaluator = RetrievalEvaluator()
        results = evaluator.run_all_evaluations(top_k=5)
        # Format summary metrics for JSON output
        summary = {name: data["metrics"] for name, data in results.items()}
        return jsonify({
            "status": "success",
            "summary": summary,
            "total_queries_tested": len(evaluator.queries),
        }), 200
    except Exception as e:
        return jsonify({"detail": f"Evaluation benchmark failed: {e}"}), 500

@ingest.route("/documents", methods=["GET"])
def list_documents():
    try:
        client = get_supabase_client()
        documents = _data(client.table("documents").select("id,title,s3_key,created_at").execute())
        chunks = _data(client.table("document_chunks").select("document_id").execute())
        counts = Counter(str(chunk["document_id"]) for chunk in chunks)
        return jsonify([_document_info(document, counts) for document in documents])
    except Exception:
        return jsonify({"detail": "Could not load documents."}), 500

@ingest.route("/documents/<document_id>", methods=["DELETE"])
def delete_document(document_id: str):
    try:
        client = get_supabase_client()
        document_rows = _data(client.table("documents").select("s3_key").eq("id", document_id).execute())
        client.table("document_chunks").delete().eq("document_id", document_id).execute()
        client.table("documents").delete().eq("id", document_id).execute()
        if document_rows and document_rows[0].get("s3_key") and S3_BUCKET_NAME:
            aws_s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=document_rows[0]["s3_key"])
        # Regenerate sparse index after deletion to keep sync
        try:
            SparseIngestion().regenerate_index()
        except Exception as sparse_err:
            print("Warning: Sparse index regeneration failed after delete:", sparse_err)
        return "", 204
    except Exception:
        return jsonify({"detail": "Could not delete document."}), 500

def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"

@ingest.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    print("payload", payload)
    message = payload.get("message")
    print("message", message)

    history = payload.get("history", [])

    # Optional retrieval configuration from request body (with defaults)
    match_count = payload.get("match_count")
    rerank = payload.get("rerank", False)
    dense_weight = payload.get("dense_weight", 1.5)
    sparse_weight = payload.get("sparse_weight", 0.5)
    document_ids = payload.get("document_ids")

    if not isinstance(message, str) or not message.strip():
        return jsonify({"detail": "A non-empty message is required."}), 400
    if not isinstance(history, list):
        return jsonify({"detail": "History must be a list."}), 400

    def generate() -> Iterator[str]:
        try:
            print("Generator started - Hybrid Retrieval")

            hybrid_retriever = HybridRetriever()
            retrieved_rows = hybrid_retriever.retrieve(
                query=message,
                match_count=match_count,
                dense_weight=dense_weight,
                sparse_weight=sparse_weight,
                rerank=rerank,
                document_ids=document_ids,
            )

            print("Hybrid retrieved rows count:", len(retrieved_rows))

            sources = [
                {
                    "chunk_id": str(row.get("id") or row.get("chunk_id") or index),
                    "doc_id": str(row.get("document_id") or row.get("doc_id") or ""),
                    "filename": row.get("title") or row.get("filename") or "Untitled document",
                    "text": row.get("content") or row.get("text") or "",
                    "score": float(
                        row.get("cross_encoder_score")
                        or row.get("rrf_score")
                        or row.get("score")
                        or row.get("similarity")
                        or 0
                    ),
                    "page_number": row.get("page_number", 1),
                }
                for index, row in enumerate(retrieved_rows)
            ]

            yield _sse({"type": "sources", "sources": sources})

            if not sources:
                yield _sse({"type": "token", "content": "I couldn't find relevant passages in the uploaded documents."})
            else:
                context = "\n\n".join(
                    f"[{index}] {source['text']}"
                    for index, source in enumerate(sources, start=1)
                )
                for token in CallLLM().stream_answer(message, context, history):
                    yield _sse({"type": "token", "content": token})

            yield _sse({"type": "done"})

        except Exception as e:
            yield _sse({"type": "error", "content": f"Unable to answer that question right now. {e}"})

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache"}
    )
