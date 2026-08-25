"""Small adapter around Gemini used by the chat endpoint."""

from collections.abc import Iterator, Sequence

from langchain_google_genai import GoogleGenerativeAI

from config.settings import GEMINI_API_KEY, GEMINI_MODEL_NAME

class CallLLM:
    def __init__(self, model_name: str = GEMINI_MODEL_NAME, api_key: str | None = GEMINI_API_KEY):
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY must be configured before using chat")
        self.llm = GoogleGenerativeAI(model=model_name, google_api_key=api_key, temperature=0.2)
    
    def stream_answer(
        self,
        question: str,
        context: str,
        history: Sequence[dict[str, str]] = (),
    ) -> Iterator[str]:
        conversation = "\n".join(
            f"{entry['role'].capitalize()}: {entry['content']}"
            for entry in history[-10:]
            if entry.get("role") in {"user", "assistant"} and entry.get("content")
        )
        prompt = f"""You are a precise document assistant. Answer only from the retrieved passages.
If the passages do not support an answer, say that clearly. Cite every factual claim using
the supplied bracket markers such as [1]. Do not invent citations.

Conversation history:
{conversation or '(none)'}

Retrieved passages:
{context}

Question: {question}
Answer:"""
        for chunk in self.llm.stream(prompt):
            yield str(chunk)


# Retain the original public name for existing imports.
Call_LLM = CallLLM
