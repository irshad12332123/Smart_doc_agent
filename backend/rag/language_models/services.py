import time
from collections.abc import Iterator, Sequence

from langchain_google_genai import GoogleGenerativeAI

try:
    from config.settings import GEMINI_API_KEY, GEMINI_MODEL_NAME
except ImportError:
    from rag.config.settings import GEMINI_API_KEY, GEMINI_MODEL_NAME

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
        subject_list: Sequence[str] = (),
    ) -> Iterator[str]:

        # print(f"context : {context} \n history: {history} \n question: {question}")
        conversation = "\n".join(
            f"{entry['role'].capitalize()}: {entry['content']}"
            for entry in history[-10:]
            if entry.get("role") in {"user", "assistant"} and entry.get("content")
        )

        prompt = f"""You are a precise academic document assistant. If the user requires an answer in a certain length, answer them accordingly, but do not exceed 1000 words. Answer only from the retrieved data.
If the data do not support an answer, say that clearly. Cite every factual claim using the supplied bracket markers such as [1]. Do not invent citations.
If the user asks for a list, provide it in a numbered format. If the user asks for a table, provide it in a markdown table format.
If the user asks for a summary, provide a concise summary of the retrieved data.

Subject and assignment validation rules:
- When a user requests assignments or materials for a specific subject, check if the subject matches any item in the provided subject_list.
  * If a match is found: Fetch and display the assignment data for that subject accordingly.
  * If no match is found: Clearly inform the user that the specified subject is not in their enrolled subject list.

Handling insufficient queries & asking for extra context:
- If the user's query is insufficient, ambiguous, or lacks necessary context to fulfill their request (for example, if a student asks for notes, assignments, syllabus, or details of a specific unit or topic like "give notes of specific unit or assignment", but does not specify the subject):
  * Do NOT assume or guess which subject they mean.
  * Proactively ask the user for clarification and more context to fulfill their request.
  * Prompt them to specify the subject or let you know if they want the information/notes for every subject.
  * If enrolled subjects are available in the Subject list, list them to guide the user in choosing.

Conversation history:
{conversation or '(none)'}

Retrieved data:
{context or '(none)'}

Subject list:
{subject_list}

Question: {question}
Answer:"""
        for chunk in self.llm.stream(prompt):
            yield str(chunk)

    def generate_answer(
        self,
        question: str,
        context: str,
        history: Sequence[dict[str, str]] = (),
        subject_list: Sequence[str] = (),
    ) -> str:
        start_time = time.perf_counter()

        # Collect the streamed response chunks into a single string
        answer = "".join(
            self.stream_answer(
                question=question,
                context=context,
                history=history,
                subject_list=subject_list,
            )
        )

        elapsed_time = time.perf_counter() - start_time
        print(f"[CallLLM] generate_answer completed in {elapsed_time:.4f} seconds.")

        return answer


# Retain the original public name for existing imports.
Call_LLM = CallLLM
