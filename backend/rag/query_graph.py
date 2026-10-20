
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END


class RAGState(TypedDict, total=False):
    query: str
    original_query: str
    route: str
    chunks: list[dict]
    attempt_count: int
    max_attempts: int
    sufficient: bool
    answer: str



def route_query(state: RAGState):
    query = state["query"]

    # Replace with your existing LLM router.
    route = classify_query(query)

    if route not in {"deterministic", "rag"}:
        route = "rag"

    return {"route": route}


def deterministic_search(state: RAGState):
    # Existing exact SQL/metadata search.
    results = search_exact_metadata(state["query"])
    return {"chunks": results}


def rag_search(state: RAGState):
    # Existing BM25 + dense retrieval + RRF + reranking.
    results = hybrid_retrieve_and_rerank(state["query"])
    return {"chunks": results}


def evaluate(state: RAGState):
    # Use relevance, evidence sufficiency and source quality.
    sufficient = evaluate_retrieval(
        query=state["original_query"],
        chunks=state.get("chunks", []),
    )
    return {"sufficient": sufficient}


def rewrite_query(state: RAGState):
    rewritten = rewrite_search_query(
        state["original_query"],
        state["query"],
        state.get("chunks", []),
    )
    return {
        "query": rewritten,
        "attempt_count": state["attempt_count"] + 1,
    }


def generate(state: RAGState):
    answer = generate_grounded_answer(
        query=state["original_query"],
        chunks=state.get("chunks", []),
    )
    return {"answer": answer}


def choose_search(state: RAGState) -> Literal[
    "deterministic_search", "rag_search"
]:
    return (
        "deterministic_search"
        if state["route"] == "deterministic"
        else "rag_search"
    )


def after_deterministic(state: RAGState) -> Literal[
    "generate", "rag_search"
]:
    # Exact lookup failed? Fall back to RAG.
    return "generate" if state.get("chunks") else "rag_search"


def after_evaluation(state: RAGState) -> Literal[
    "generate", "rewrite_query"
]:
    if state.get("sufficient"):
        return "generate"

    if state["attempt_count"] >= state["max_attempts"]:
        return "generate"

    return "rewrite_query"


builder = StateGraph(RAGState)

builder.add_node("router", route_query)
builder.add_node("deterministic_search", deterministic_search)
builder.add_node("rag_search", rag_search)
builder.add_node("evaluate", evaluate)
builder.add_node("rewrite_query", rewrite_query)
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
