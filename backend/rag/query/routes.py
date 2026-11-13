"""HTTP routes for retrieval, evaluation, and chat."""

import json
import logging
from collections.abc import Iterator
from typing import Any

from flask import Blueprint, Response, jsonify, request, stream_with_context

from evaluation.evaluator import RetrievalEvaluator
from lib.supabase import get_supabase_client
from modules.auth.middleware import require_auth
from modules.user.services import get_subjects
from query_graph import RAGState, query_graph
from services.retriever.hybrid import HybridRetriever
from services.retriever.sparse import SparseRetriever

logger = logging.getLogger(__name__)

query = Blueprint("query", __name__, url_prefix="/api")


@query.post("/retrieve/sparse")
def retrieve_sparse():
    """Retrieve document chunks using the BM25 sparse retriever."""
    payload = request.get_json(silent=True) or {}
    query_text = payload.get("query")
    if not isinstance(query_text, str) or not query_text.strip():
        return jsonify({"detail": "Query string is required"}), 400

    try:
        results = SparseRetriever().retrieve(
            query=query_text,
            match_count=payload.get("match_count"),
            match_threshold=payload.get("match_threshold", 0.0),
            document_ids=payload.get("document_ids"),
        )
        return jsonify({"query": query_text, "results": results, "count": len(results)}), 200
    except Exception as error:
        return jsonify({"detail": f"Sparse retrieval failed: {error}"}), 500


@query.post("/retrieve/hybrid")
def retrieve_hybrid():
    """Retrieve document chunks using the hybrid retriever."""
    payload = request.get_json(silent=True) or {}
    query_text = payload.get("query")
    if not isinstance(query_text, str) or not query_text.strip():
        return jsonify({"detail": "Query string is required"}), 400

    rerank = payload.get("rerank", False)
    try:
        results = HybridRetriever().retrieve(
            query=query_text,
            match_count=payload.get("match_count"),
            dense_weight=payload.get("dense_weight", 1.0),
            sparse_weight=payload.get("sparse_weight", 1.0),
            rerank=rerank,
            document_ids=payload.get("document_ids"),
        )
        return jsonify(
            {
                "query": query_text,
                "reranked": rerank,
                "results": results,
                "count": len(results),
            }
        ), 200
    except Exception as error:
        return jsonify({"detail": f"Hybrid retrieval failed: {error}"}), 500


@query.route("/evaluation/run", methods=["POST", "GET"])
def run_evaluation():
    """Run retrieval benchmark evaluation on the college dataset."""
    try:
        evaluator = RetrievalEvaluator()
        results = evaluator.run_all_evaluations(top_k=5)
        return jsonify(
            {
                "status": "success",
                "summary": {name: data["metrics"] for name, data in results.items()},
                "total_queries_tested": len(evaluator.queries),
            }
        ), 200
    except Exception as error:
        return jsonify({"detail": f"Evaluation benchmark failed: {error}"}), 500


def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@query.post("/chat")
@require_auth
def chat():
    payload = request.get_json(silent=True) or {}
    message = payload.get("message") or payload.get("query")
    history = payload.get("history", [])

    if not isinstance(message, str) or not message.strip():
        return jsonify({"detail": "A non-empty message is required."}), 400
    if not isinstance(history, list):
        return jsonify({"detail": "History must be a list."}), 400

    raw_subject_list = []
    try:
        raw_subject_list = get_subjects(get_supabase_client())
    except Exception as error:
        logger.warning("Could not retrieve subjects for chat: %s", error)

    match_count = payload.get("match_count")
    rerank = payload.get("rerank", False)
    dense_weight = payload.get("dense_weight", 1.5)
    sparse_weight = payload.get("sparse_weight", 0.5)
    document_ids = payload.get("document_ids")
    max_attempts = payload.get("max_attempts", 2)

    def generate() -> Iterator[str]:
        try:
            initial_state: RAGState = {
                "query": message.strip(),
                "original_query": message.strip(),
                "subject_list": raw_subject_list,
                "history": history,
                "match_count": match_count,
                "rerank": rerank,
                "dense_weight": dense_weight,
                "sparse_weight": sparse_weight,
                "document_ids": document_ids,
                "attempt_count": 0,
                "max_attempts": max_attempts,
            }
            result = query_graph.invoke(initial_state)

            if result.get("documents"):
                yield _sse({"type": "documents", "documents": result["documents"]})
            if result.get("sources"):
                yield _sse({"type": "sources", "sources": result["sources"]})
            if result.get("answer"):
                yield _sse({"type": "token", "content": result["answer"]})
            yield _sse({"type": "done"})
        except Exception as error:
            logger.exception("Error in chat orchestration:")
            yield _sse(
                {
                    "type": "error",
                    "content": f"Unable to answer that question right now. {error}",
                }
            )

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
