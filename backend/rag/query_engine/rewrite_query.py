import logging
from typing import Any, Optional, Sequence

try:
    from language_models.sml import load_slm
except ImportError:
    from rag.language_models.sml import load_slm

logger = logging.getLogger(__name__)


def format_history_context(
    history: Optional[Sequence[dict[str, Any]]],
    max_turns: int = 4,
    max_char_per_message: int = 300,
) -> str:
    """
    Extracts and formats recent conversation history to a limited extent.
    Keeps the last `max_turns` interactions and truncates message text
    to avoid context blowup.
    """
    if not history:
        return ""

    formatted_turns: list[str] = []
    # Take at most the last 2 * max_turns messages (user and assistant pairs)
    recent_entries = list(history)[-(max_turns * 2):]

    for entry in recent_entries:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role", "")
        content = entry.get("content", "")
        if role in {"user", "assistant"} and content and isinstance(content, str):
            clean_content = content.strip()
            if not clean_content:
                continue
            if len(clean_content) > max_char_per_message:
                clean_content = clean_content[:max_char_per_message] + "..."
            formatted_turns.append(f"{role.capitalize()}: {clean_content}")

    return "\n".join(formatted_turns)


def rewrite_query(
    query: str,
    model: str,
    history: Optional[Sequence[dict[str, Any]]] = None,
    max_history_turns: int = 4,
) -> str:
    """
    Rewrites the user query to make it self-contained and optimized for vector/keyword retrieval.
    If conversation history is provided, incorporates context (resolving pronouns, implicit references)
    to a limited extent while maintaining conciseness.
    If history is absent or empty, refines the query standalone.
    """
    if not query or not query.strip():
        return query

    original_query = query.strip()

    try:
        client = load_slm()
    except Exception as e:
        logger.warning(f"Failed to load SLM client for query rewriting: {e}")
        return original_query

    history_context = format_history_context(history, max_turns=max_history_turns)

    if history_context:
        prompt = f"""You are a query rewriting assistant for an academic retrieval system.
Your task is to rewrite the user's latest query into a clear, standalone search query optimized for database and vector retrieval.

Recent conversation history:
{history_context}

Latest user query: "{original_query}"

Instructions:
1. If the user query references prior conversation topics (such as pronouns like "it", "they", "this", or follow-up phrases like "what about the second one?", "explain more"), incorporate the necessary context from history to produce a fully self-contained search query.
2. If the user query is already self-contained or starts a new topic, keep it concise and focused without injecting unrelated history.
3. Output ONLY the rewritten query in a single line, with no explanations, preambles, or quotes.
"""
    else:
        prompt = f"""You are a query rewriting assistant for an academic retrieval system.
Your task is to rewrite the user's query to be clear, concise, and optimized for retrieving relevant information from a database.

User's query: "{original_query}"

Instructions:
1. Rephrase the query into a focused, standalone search query for document retrieval.
2. Avoid adding any extra facts not implied by the query.
3. Output ONLY the rewritten query in a single line, with no explanations, preambles, or quotes.
"""

    try:
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful query rewriting assistant. Respond only with the rewritten query.",
                },
                {"role": "user", "content": prompt},
            ],
            model=model,
            temperature=0.1,
            max_tokens=100,
        )

        if not response.choices or not response.choices[0].message:
            return original_query

        rewritten = response.choices[0].message.content or ""
        rewritten = rewritten.strip()

        # Remove accidental surrounding quotes
        if (rewritten.startswith('"') and rewritten.endswith('"')) or (
            rewritten.startswith("'") and rewritten.endswith("'")
        ):
            rewritten = rewritten[1:-1].strip()

        return rewritten if rewritten else original_query

    except Exception as e:
        logger.warning(f"Query rewriting failed with error: {e}. Falling back to original query.")
        return original_query
