from measure_time_taken.time_taken import measure_node
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
    logger.warning(f"Routing query: {state.get('query') or state.get('original_query', '')}")
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

    explicit_route = state.get("route") if attempt_count == 0 else None
    if explicit_route:
        normalized_route = "deterministic" if explicit_route in {"deterministic", "metadata"} else "rag"
        return {
            "query": query,
            "original_query": original_query,
            "route": normalized_route,
            "attempt_count": attempt_count,
            "max_attempts": max_attempts,
        }

    # If already on the deterministic route (e.g. during a rewrite retry), stay deterministic
    # without re-deciding route or falling back to RAG.
    if state.get("route") in {"deterministic", "metadata"}:
        try:
            router = DocumentRouter()
            result: RouterResult = router.route(
                query=query,
                subject_list=subject_list,
                history=history,
            )
            formatted_text = result.formatted_text if (result.documents and len(result.documents) > 0) else None
            return {
                "query": query,
                "original_query": original_query,
                "route": "deterministic",
                "chunks": result.documents or [],
                "documents": result.documents or [],
                "formatted_text": formatted_text,
                "intent": result.intent,
                "attempt_count": attempt_count,
                "max_attempts": max_attempts,
            }
        except Exception as e:
            logger.warning(f"Error during deterministic retry routing: {e}.")
            return {
                "query": query,
                "original_query": original_query,
                "route": "deterministic",
                "chunks": [],
                "documents": [],
                "formatted_text": None,
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

        formatted_text = result.formatted_text if (result.documents and len(result.documents) > 0) else None
        return {
            "query": query,
            "original_query": original_query,
            "route": route,
            "chunks": result.documents or [],
            "documents": result.documents or [],
            "formatted_text": formatted_text,
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
    logger.warning(f"Choosing search method based on route: {state.get('route')}")
    """
    Conditional edge: routes to deterministic search if route is metadata/deterministic,
    otherwise routes to hybrid RAG search.
    """
    if state.get("route") in {"deterministic", "metadata"}:
        return "deterministic_search"
    return "rag_search"


def deterministic_search(state: RAGState) -> dict[str, Any]:
    logger.warning(f"Performing deterministic search for query: {state.get('query') or state.get('original_query', '')}")
    """
    Performs deterministic SQL/metadata document lookup.
    """
    existing_chunks = state.get("chunks") or state.get("documents") or []
    if existing_chunks:
        formatted_text = state.get("formatted_text")
        if not formatted_text and state.get("intent"):
            try:
                router = DocumentRouter()
                formatted_text = router._format_document_list(existing_chunks, state.get("intent"))
            except Exception:
                formatted_text = None
        return {
            "chunks": existing_chunks,
            "documents": existing_chunks,
            "formatted_text": formatted_text,
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

        formatted_text = None
        if docs:
            if state.get("formatted_text"):
                formatted_text = state.get("formatted_text")
            elif intent:
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


def after_deterministic(state: RAGState) -> Literal["evaluate", "rewrite_query", "generate"]:
    """
    Conditional edge:
    - If deterministic exact lookup finds documents, proceeds to evaluation.
    - If deterministic lookup fails/finds no documents and this is the first attempt (attempt_count == 0),
      routes to rewrite_query for a single retry attempt (no max_attempts loop).
    - If file not found after that single try, routes directly to generate without re-deciding route or looping again.
    """
    has_chunks = bool(state.get("chunks") or state.get("documents"))
    logger.warning(f"After deterministic search - Chunks found: {has_chunks}")
    if has_chunks:
        return "evaluate"

    attempt_count = state.get("attempt_count", 0)
    if attempt_count == 0:
        logger.info(
            "Deterministic search failed to find documents (attempt 0). Routing to rewrite_query (single try)."
        )
        return "rewrite_query"

    logger.info(
        f"Deterministic search failed to find documents after rewrite (attempt {attempt_count}). "
        "Routing directly to generate without re-deciding route or looping again."
    )
    return "generate"


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
            "documents": [],
            "formatted_text": None,
            "route": "rag",
        }
    except Exception as e:
        logger.warning(f"Hybrid retrieval failed: {e}")
        return {
            "chunks": [],
            "sources": [],
            "documents": [],
            "formatted_text": None,
            "route": "rag",
            "error": str(e),
        }


def evaluate(state: RAGState) -> dict[str, Any]:
    logger.warning(f"Evaluating retrieved evidence for query: {state.get('query') or state.get('original_query', '')}")
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
                "extra_info_required": False,
            },
        }

    try:
        evidence_payload = []
        for chunk in chunks:
            text = chunk.get("content") or chunk.get("text")
            if not text:
                meta_parts = []
                if chunk.get("title") or chunk.get("filename"):
                    meta_parts.append(f"Title: {chunk.get('title') or chunk.get('filename')}")
                if chunk.get("document_type"):
                    meta_parts.append(f"Type: {chunk.get('document_type')}")
                if chunk.get("subject_name"):
                    meta_parts.append(f"Subject: {chunk.get('subject_name')}")
                if chunk.get("unit") is not None:
                    meta_parts.append(f"Unit: {chunk.get('unit')}")
                if chunk.get("description"):
                    meta_parts.append(f"Description: {chunk.get('description')}")
                if chunk.get("deadline"):
                    meta_parts.append(f"Deadline: {chunk.get('deadline')}")
                text = " | ".join(meta_parts) if meta_parts else (chunk.get("title") or chunk.get("filename") or "")

            evidence_payload.append({
                "text": text,
                "title": chunk.get("title") or chunk.get("filename") or "",
            })
        evaluator = EvidenceEvaluator(query=query, evidence=evidence_payload)
        eval_result = evaluator.evaluate()
        sufficient = bool(eval_result.get("sufficiency", False))

        return {
            "sufficient": sufficient,
            "evaluation": eval_result,
        }
    except Exception as e:
        logger.warning(f"Evidence evaluation failed: {e}. Defaulting to insufficient to trigger rewrite loop.")
        return {
            "sufficient": False,
            "evaluation": {
                "relevance": False,
                "sufficiency": False,
                "quality": False,
                "scores": {"relevance": 0.0, "sufficiency": 0.0, "quality": 0.0},
                "reason": f"Evaluation error fallback: {e}",
                "extra_info_required": False,
            },
        }


def after_evaluation(state: RAGState) -> Literal["generate", "rewrite_query"]:
    logger.warning(f"After evaluation - Sufficient: {state.get('sufficient')}")
    """
    Conditional edge: if evidence is evaluated as sufficient, extra info is required, or max attempts reached,
    proceeds to generate answer. Otherwise, rewrites the query for another retrieval attempt.
    """
    if state.get("sufficient"):
        return "generate"

    evaluation = state.get("evaluation") or {}
    if evaluation.get("extra_info_required"):
        logger.info("Extra user clarification required; bypassing rewrite loop to generate clarification prompt.")
        return "generate"

    attempt_count = state.get("attempt_count", 0)
    max_attempts = state.get("max_attempts", 2)
    if attempt_count >= max_attempts:
        return "generate"

    return "rewrite_query"


def rewrite_query_node(state: RAGState) -> dict[str, Any]:
    current_attempt = state.get("attempt_count", 0)
    current_query = state.get("query") or state.get("original_query", "")
    original_query = state.get("original_query") or current_query
    logger.warning(
        f"Rewriting query (attempt {current_attempt + 1}) for: {current_query}"
    )
    """
    Rewrites the search query using Groq SLM to improve retrieval precision.
    """
    history = state.get("history")
    evaluation = state.get("evaluation") or {}
    feedback = evaluation.get("reason")

    if not feedback:
        if state.get("route") in {"deterministic", "metadata"} or state.get("intent"):
            feedback = (
                "A previous deterministic document lookup returned 0 matching documents. "
                "Reformulate the query to clarify the target subject, unit, or document type keywords."
            )
        else:
            feedback = "A previous retrieval attempt did not return sufficient or relevant documents."

    try:
        rewritten = rewrite_query(
            query=current_query,
            model=GROQ_MODEL,
            history=history,
            feedback=feedback,
            attempt=current_attempt + 1,
            original_query=original_query,
        )
        logger.warning(f"Rewritten query: {rewritten}")
    except Exception as e:
        logger.warning(f"Query rewrite failed: {e}. Retaining current query.")
        rewritten = current_query

    # If this rewrite came from after_deterministic (file not found in deterministic search, no evaluation),
    # preserve route as "deterministic" so it retries deterministically without re-deciding route to RAG.
    # If it came from after_evaluation (insufficient evidence for detailed question), allow re-routing.
    is_from_deterministic_search = state.get("route") in {"deterministic", "metadata"} and not state.get("evaluation")
    preserved_route = "deterministic" if is_from_deterministic_search else None

    return {
        "query": rewritten,
        "attempt_count": current_attempt + 1,
        "formatted_text": None,
        "documents": [],
        "chunks": [],
        "route": preserved_route,
        "intent": None,
        "sufficient": False,
        "evaluation": None,
    }


def generate(state: RAGState) -> dict[str, Any]:
    logger.warning(f"Generating answer for query: {state.get('query') or state.get('original_query', '')}")
    """
    Generates a grounded final answer using LLM with reasoning over retrieved evidence/documents.
    """
    evaluation = state.get("evaluation") or {}
    is_extra_info_needed = bool(evaluation.get("extra_info_required"))
    chunks = state.get("chunks", [])

    # If formatted_text is provided without raw chunks, return it directly
    if state.get("formatted_text") and not chunks and not is_extra_info_needed and state.get("sufficient", True):
        return {"answer": state["formatted_text"]}

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

    context_entries = []
    for idx, chunk in enumerate(chunks, start=1):
        content = chunk.get("content") or chunk.get("text")
        meta_parts = []
        if chunk.get("title") or chunk.get("filename"):
            meta_parts.append(f"Title: {chunk.get('title') or chunk.get('filename')}")
        if chunk.get("document_type"):
            meta_parts.append(f"Type: {chunk.get('document_type')}")
        if chunk.get("subject_name"):
            meta_parts.append(f"Subject: {chunk.get('subject_name')}")
        if chunk.get("unit") is not None:
            meta_parts.append(f"Unit: {chunk.get('unit')}")
        if chunk.get("deadline"):
            meta_parts.append(f"Deadline: {chunk.get('deadline')}")
        if chunk.get("description"):
            meta_parts.append(f"Description: {chunk.get('description')}")
        if chunk.get("file_url") or chunk.get("url"):
            meta_parts.append(f"File URL: {chunk.get('file_url') or chunk.get('url')}")

        if content and meta_parts:
            entry = f"[{idx}] " + " | ".join(meta_parts) + f"\nContent: {content}"
        elif content:
            entry = f"[{idx}] {content}"
        elif meta_parts:
            entry = f"[{idx}] " + " | ".join(meta_parts)
        else:
            entry = f"[{idx}] (Empty document)"

        context_entries.append(entry)

    context = "\n\n".join(context_entries)

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
        if state.get("formatted_text"):
            return {"answer": state["formatted_text"]}
        return {
            "answer": f"Unable to generate an answer right now. Context retrieved ({len(chunks)} chunks).",
            "error": str(e),
        }

# Orchestration Graph Construction
builder = StateGraph(RAGState)

# Register nodes with performance measurement
builder.add_node("router",
    measure_node("router", route_query))

builder.add_node("deterministic_search",
    measure_node("deterministic_search", deterministic_search))

builder.add_node("rag_search",
    measure_node("rag_search", rag_search))

builder.add_node("evaluate",
    measure_node("evaluate", evaluate))

builder.add_node("rewrite_query",
    measure_node("rewrite_query", rewrite_query_node))

builder.add_node("generate",
    measure_node("generate", generate))


# Define graph edges
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

builder.add_edge("rewrite_query", "router")
builder.add_edge("generate", END)


# Compile only after registering nodes and edges
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
