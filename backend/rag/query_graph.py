import json
import logging
from typing import Any, Literal, Optional, Sequence, TypedDict

from langgraph.graph import StateGraph, START, END

try:
    from backend.rag.config.settings import GROQ_MODEL
    from backend.rag.documents.service import DocumentService
    from backend.rag.evaluator.evidence_evaluator import EvidenceEvaluator
    from backend.rag.intent.schema import DocumentIntent
    from backend.rag.language_models.services import CallLLM
    from backend.rag.query_engine.rewrite_query import rewrite_query
    from backend.rag.query_engine.router import DocumentRouter, RouterResult
    from backend.rag.services.retriever.hybrid import HybridRetriever
except ImportError:
    try:
        from rag.config.settings import GROQ_MODEL
        from rag.documents.service import DocumentService
        from rag.evaluator.evidence_evaluator import EvidenceEvaluator
        from rag.intent.schema import DocumentIntent
        from rag.language_models.services import CallLLM
        from rag.query_engine.rewrite_query import rewrite_query
        from rag.query_engine.router import DocumentRouter, RouterResult
        from rag.services.retriever.hybrid import HybridRetriever
    except ImportError:
        from config.settings import GROQ_MODEL
        from documents.service import DocumentService
        from evaluator.evidence_evaluator import EvidenceEvaluator
        from intent.schema import DocumentIntent
        from language_models.services import CallLLM
        from query_engine.rewrite_query import rewrite_query
        from query_engine.router import DocumentRouter, RouterResult
        from services.retriever.hybrid import HybridRetriever

logger = logging.getLogger(__name__)


class RAGState(TypedDict, total=False):
    query: str
    original_query: str
    route: str  # 'deterministic' | 'rag'
    chunks: list[dict[str, Any]]
    documents: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    formatted_text: Optional[str]
    intent: Optional[Any]  # DocumentIntent
    attempt_count: int
    max_attempts: int
    sufficient: bool
    evaluation: Optional[dict[str, Any]]
    answer: str
    # Context & optional configuration parameters
    history: Optional[Sequence[dict[str, Any]]]
    subject_list: Optional[Sequence[Any]]
    match_count: Optional[int]
    rerank: Optional[bool]
    dense_weight: Optional[float]
    sparse_weight: Optional[float]
    document_ids: Optional[list[str]]
    error: Optional[str]


def route_query(state: RAGState) -> dict[str, Any]:
    """
    Analyzes the query and determines routing between deterministic metadata lookup and hybrid RAG.
    Uses DocumentRouter to extract intent and check deterministic document availability.
    """
    query = state.get("query") or state.get("original_query", "")
    original_query = state.get("original_query") or query
    attempt_count = state.get("attempt_count", 0)
    max_attempts = state.get("max_attempts", 2)
    subject_list = state.get("subject_list")
    history = state.get("history")

    explicit_route = state.get("route")
    if explicit_route:
        normalized_route = "deterministic" if explicit_route in {"deterministic", "metadata"} else "rag"
        return {
            "query": query,
            "original_query": original_query,
            "route": normalized_route,
            "attempt_count": attempt_count,
            "max_attempts": max_attempts,
        }

    try:
        router = DocumentRouter()
        result: RouterResult = router.route(
            query=query,
            subject_list=subject_list,
            history=history,
        )

        if result.route == "metadata" and not result.should_invoke_rag:
            route = "deterministic"
        else:
            route = "rag"

        return {
            "query": query,
            "original_query": original_query,
            "route": route,
            "chunks": result.documents or [],
            "documents": result.documents or [],
            "formatted_text": result.formatted_text,
            "intent": result.intent,
            "attempt_count": attempt_count,
            "max_attempts": max_attempts,
        }
    except Exception as e:
        logger.warning(f"Error during query routing: {e}. Falling back to RAG.")
        return {
            "query": query,
            "original_query": original_query,
            "route": "rag",
            "attempt_count": attempt_count,
            "max_attempts": max_attempts,
            "error": str(e),
        }


def choose_search(state: RAGState) -> Literal["deterministic_search", "rag_search"]:
    """
    Conditional edge: routes to deterministic search if route is metadata/deterministic,
    otherwise routes to hybrid RAG search.
    """
    if state.get("route") in {"deterministic", "metadata"}:
        return "deterministic_search"
    return "rag_search"


def deterministic_search(state: RAGState) -> dict[str, Any]:
    """
    Performs deterministic SQL/metadata document lookup.
    """
    existing_chunks = state.get("chunks") or state.get("documents") or []
    if existing_chunks:
        return {
            "chunks": existing_chunks,
            "documents": existing_chunks,
        }

    intent = state.get("intent")
    query = state.get("query") or state.get("original_query", "")

    try:
        doc_service = DocumentService()
        if intent:
            docs = doc_service.lookup_documents(intent, generate_signed_urls=True)
        else:
            router = DocumentRouter()
            router_res = router.route(
                query,
                subject_list=state.get("subject_list"),
                history=state.get("history"),
            )
            docs = router_res.documents
            intent = router_res.intent

        formatted_text = state.get("formatted_text")
        if not formatted_text and docs and intent:
            router = DocumentRouter()
            formatted_text = router._format_document_list(docs, intent)

        return {
            "chunks": docs,
            "documents": docs,
            "formatted_text": formatted_text,
        }
    except Exception as e:
        logger.warning(f"Deterministic search failed: {e}")
        return {
            "chunks": [],
            "documents": [],
            "error": str(e),
        }


def after_deterministic(state: RAGState) -> Literal["generate", "rag_search"]:
    """
    Conditional edge: if deterministic exact lookup succeeds, proceeds to generation.
    If exact lookup returns no documents, falls back to hybrid RAG search.
    """
    return "generate" if bool(state.get("chunks")) else "rag_search"


def rag_search(state: RAGState) -> dict[str, Any]:
    """
    Executes hybrid retrieval (BM25 sparse + dense embeddings + RRF + optional cross-encoder reranking).
    """
    query = state.get("query") or state.get("original_query", "")
    match_count = state.get("match_count")
    rerank = state.get("rerank", False)
    dense_weight = state.get("dense_weight", 1.5)
    sparse_weight = state.get("sparse_weight", 0.5)
    document_ids = state.get("document_ids")

    try:
        retriever = HybridRetriever()
        retrieved_rows = retriever.retrieve(
            query=query,
            match_count=match_count,
            dense_weight=dense_weight,
            sparse_weight=sparse_weight,
            rerank=rerank,
            document_ids=document_ids,
        )

        sources = [
            {
                "chunk_id": str(row.get("id") or row.get("chunk_id") or idx),
                "doc_id": str(row.get("document_id") or row.get("doc_id") or ""),
                "filename": row.get("title") or row.get("filename") or "Untitled document",
                "text": row.get("content") or row.get("text") or "",
                "score": float(
                    row.get("cross_encoder_score")
                    or row.get("rrf_score")
                    or row.get("score")
                    or row.get("similarity")
                    or 0.0
                ),
                "page_number": row.get("page_number", 1),
            }
            for idx, row in enumerate(retrieved_rows)
        ]

        return {
            "chunks": retrieved_rows,
            "sources": sources,
        }
    except Exception as e:
        logger.warning(f"Hybrid retrieval failed: {e}")
        return {
            "chunks": [],
            "sources": [],
            "error": str(e),
        }


def evaluate(state: RAGState) -> dict[str, Any]:
    """
    Evaluates retrieved evidence using EvidenceEvaluator for relevance, sufficiency, and quality.
    """
    query = state.get("original_query") or state.get("query", "")
    chunks = state.get("chunks", [])

    if not chunks:
        return {
            "sufficient": False,
            "evaluation": {
                "relevance": False,
                "sufficiency": False,
                "quality": False,
                "scores": {"relevance": 0.0, "sufficiency": 0.0, "quality": 0.0},
                "reason": "No evidence retrieved.",
            },
        }

    try:
        evidence_payload = [
            {
                "text": chunk.get("content") or chunk.get("text") or chunk.get("description") or "",
                "title": chunk.get("title") or chunk.get("filename") or "",
            }
            for chunk in chunks
        ]
        evaluator = EvidenceEvaluator(query=query, evidence=evidence_payload)
        eval_result = evaluator.evaluate()
        sufficient = bool(eval_result.get("sufficiency", False))

        return {
            "sufficient": sufficient,
            "evaluation": eval_result,
        }
    except Exception as e:
        logger.warning(f"Evidence evaluation failed: {e}. Defaulting to sufficient if chunks exist.")
        return {
            "sufficient": bool(chunks),
            "evaluation": {
                "relevance": bool(chunks),
                "sufficiency": bool(chunks),
                "quality": bool(chunks),
                "reason": f"Evaluation error fallback: {e}",
            },
        }


def after_evaluation(state: RAGState) -> Literal["generate", "rewrite_query"]:
    """
    Conditional edge: if evidence is evaluated as sufficient or max attempts reached,
    proceeds to generate answer. Otherwise, rewrites the query for another retrieval attempt.
    """
    if state.get("sufficient"):
        return "generate"

    attempt_count = state.get("attempt_count", 0)
    max_attempts = state.get("max_attempts", 2)
    if attempt_count >= max_attempts:
        return "generate"

    return "rewrite_query"


def rewrite_query_node(state: RAGState) -> dict[str, Any]:
    """
    Rewrites the search query using Groq SLM to improve retrieval precision.
    """
    original_query = state.get("original_query") or state.get("query", "")
    history = state.get("history")
    current_attempt = state.get("attempt_count", 0)

    try:
        rewritten = rewrite_query(
            query=original_query,
            model=GROQ_MODEL,
            history=history,
        )
    except Exception as e:
        logger.warning(f"Query rewrite failed: {e}. Retaining current query.")
        rewritten = state.get("query") or original_query

    return {
        "query": rewritten,
        "attempt_count": current_attempt + 1,
    }


def generate(state: RAGState) -> dict[str, Any]:
    """
    Generates a grounded final answer using LLM or returns formatted deterministic lookup.
    """
    if state.get("formatted_text"):
        return {"answer": state["formatted_text"]}

    chunks = state.get("chunks", [])
    if not chunks:
        return {"answer": "I couldn't find relevant passages in the uploaded documents."}

    # Deterministic metadata search results without formatted_text
    if state.get("route") in {"deterministic", "metadata"} and any(
        "file_url" in c or "s3_key" in c for c in chunks
    ):
        router = DocumentRouter()
        formatted = router._format_document_list(chunks, state.get("intent"))
        return {"answer": formatted}

    query = state.get("original_query") or state.get("query", "")
    history = state.get("history") or []
    raw_subject_list = state.get("subject_list") or []

    if isinstance(raw_subject_list, list):
        subject_list_names = [
            str(s).strip() if isinstance(s, (str, int)) else str(s.get("name", "")).strip()
            for s in raw_subject_list
            if s
        ]
        subject_list_names = [s for s in subject_list_names if s]
    else:
        subject_list_names = []

    context = "\n\n".join(
        f"[{idx}] {chunk.get('content') or chunk.get('text') or chunk.get('description') or ''}"
        for idx, chunk in enumerate(chunks, start=1)
    )

    try:
        caller = CallLLM()
        answer = caller.generate_answer(
            question=query,
            context=context,
            history=history,
            subject_list=subject_list_names,
        )
        return {"answer": answer}
    except Exception as e:
        logger.warning(f"Grounded generation failed: {e}")
        return {
            "answer": f"Unable to generate an answer right now. Context retrieved ({len(chunks)} chunks).",
            "error": str(e),
        }


# Orchestration Graph Construction
builder = StateGraph(RAGState)

builder.add_node("router", route_query)
builder.add_node("deterministic_search", deterministic_search)
builder.add_node("rag_search", rag_search)
builder.add_node("evaluate", evaluate)
builder.add_node("rewrite_query", rewrite_query_node)
builder.add_node("generate", generate)

builder.add_edge(START, "router")

builder.add_conditional_edges(
    "router",
    choose_search,
)

builder.add_conditional_edges(
    "deterministic_search",
    after_deterministic,
)

builder.add_edge("rag_search", "evaluate")

builder.add_conditional_edges(
    "evaluate",
    after_evaluation,
)

builder.add_edge("rewrite_query", "rag_search")
builder.add_edge("generate", END)

query_graph = builder.compile()


def run_query(
    query: str,
    subject_list: Optional[Sequence[Any]] = None,
    history: Optional[Sequence[dict[str, Any]]] = None,
    max_attempts: int = 2,
    **kwargs: Any,
) -> RAGState:
    """
    Executes the query orchestration graph from end to end.
    """
    initial_state: RAGState = {
        "query": query,
        "original_query": query,
        "subject_list": subject_list,
        "history": history,
        "attempt_count": 0,
        "max_attempts": max_attempts,
        **kwargs,
    }
    return query_graph.invoke(initial_state)
