import json
import logging
from typing import Any, Optional, Sequence

from documents.service import DocumentService
from intent.extractor import IntentExtractor
from intent.schema import DocumentIntent, SubjectContext

logger = logging.getLogger(__name__)


class RouterResult:
    """
    Represents the output of the query routing process.
    """

    def __init__(
        self,
        route: str,  # 'metadata' | 'hybrid'
        intent: DocumentIntent,
        documents: list[dict[str, Any]],
        formatted_text: Optional[str] = None,
        should_invoke_rag: bool = False,
        resolved_subject_id: Optional[str] = None,
        filter_document_ids: Optional[list[str]] = None,
    ):
        self.route = route
        self.intent = intent
        self.documents = documents
        self.formatted_text = formatted_text
        self.should_invoke_rag = should_invoke_rag
        self.resolved_subject_id = resolved_subject_id
        self.filter_document_ids = filter_document_ids

    def to_dict(self) -> dict[str, Any]:
        return {
            "route": self.route,
            "intent": self.intent.model_dump(),
            "documents_count": len(self.documents),
            "should_invoke_rag": self.should_invoke_rag,
            "resolved_subject_id": self.resolved_subject_id,
        }


class DocumentRouter:
    """
    Deterministic Document and Retrieval Router.
    Analyzes queries via the SLM, validates metadata, routes listing and exact searches
    to the Supabase deterministic layer, and dispatches conceptual questions to Hybrid RAG.
    """

    def __init__(
        self,
        intent_extractor: Optional[IntentExtractor] = None,
        document_service: Optional[DocumentService] = None,
    ):
        self.intent_extractor = intent_extractor or IntentExtractor()
        self.document_service = document_service or DocumentService()

    def _format_document_list(
        self,
        docs: list[dict[str, Any]],
        intent: DocumentIntent,
        subject_name: Optional[str] = None,
    ) -> str:
        """
        Formats retrieved documents into a clean, markdown-formatted response for the user.
        """
        doc_type_display = (intent.document_type or "document").replace("_", " ")

        if not docs:
            if subject_name:
                return f"I couldn't find any {doc_type_display}s for **{subject_name}** in your records."
            elif intent.search_query:
                return f"I couldn't find any documents matching '{intent.search_query}'."
            return f"I couldn't find any {doc_type_display}s matching your request."

        subject_header = f" for **{subject_name}**" if subject_name else ""
        header = f"Here are the {doc_type_display}s{subject_header} ({len(docs)} found):\n\n"

        lines = [header]
        for idx, doc in enumerate(docs, start=1):
            title = doc.get("title") or "Untitled document"
            desc = doc.get("description")
            deadline = doc.get("deadline")
            file_url = doc.get("file_url")

            item_lines = [f"{idx}. **{title}**"]
            if deadline:
                # Simple friendly date presentation if ISO
                clean_deadline = deadline.replace("T", " ").split(".")[0]
                item_lines.append(f"   - **Deadline:** {clean_deadline}")
            if desc:
                # Show first 150 chars of description
                snippet = desc[:150] + "…" if len(desc) > 150 else desc
                item_lines.append(f"   - **Description:** {snippet}")
            if file_url:
                item_lines.append(f"   - [📥 Download / View File]({file_url})")

            lines.append("\n".join(item_lines) + "\n")

        return "\n".join(lines).strip()

    def route(
        self,
        query: str,
        subject_list: Sequence[Any] | None = None,
        history: Sequence[dict[str, str]] | None = None,
    ) -> RouterResult:
        """
        Main query routing pipeline:
        1. Extract structured intent via SLM.
        2. Validate fields against authorized subject context.
        3. Execute deterministic lookup for metadata queries.
        4. Fallback or route to hybrid retrieval when needed.
        """
        normalized_subjects = self.intent_extractor.normalize_subjects(subject_list)
        subject_lookup = {s.id: s.name for s in normalized_subjects}

        # Step 1: Extract intent
        intent = self.intent_extractor.extract(query, subject_list=normalized_subjects)
        matched_subject_name = subject_lookup.get(intent.subject_id) if intent.subject_id else None

        # Step 2: Route determination
        if intent.intent == "document_listing":
            route = "metadata"
            self._log_observability(intent, route)

            docs = self.document_service.lookup_documents(intent, generate_signed_urls=True)
            formatted_text = self._format_document_list(docs, intent, matched_subject_name)

            return RouterResult(
                route=route,
                intent=intent,
                documents=docs,
                formatted_text=formatted_text,
                should_invoke_rag=False,
                resolved_subject_id=intent.subject_id,
            )

        elif intent.intent == "document_search":
            # Attempt deterministic metadata search first
            route = "metadata"
            docs = self.document_service.lookup_documents(intent, generate_signed_urls=True)

            if len(docs) > 0:
                self._log_observability(intent, "metadata")
                formatted_text = self._format_document_list(docs, intent, matched_subject_name)
                return RouterResult(
                    route="metadata",
                    intent=intent,
                    documents=docs,
                    formatted_text=formatted_text,
                    should_invoke_rag=False,
                    resolved_subject_id=intent.subject_id,
                )
            else:
                # Insufficient metadata results -> Fallback to Hybrid Retrieval
                self._log_observability(intent, "hybrid")
                return RouterResult(
                    route="hybrid",
                    intent=intent,
                    documents=[],
                    formatted_text=None,
                    should_invoke_rag=True,
                    resolved_subject_id=intent.subject_id,
                )

        else:  # normal_rag_query
            route = "hybrid"
            self._log_observability(intent, route)
            return RouterResult(
                route=route,
                intent=intent,
                documents=[],
                formatted_text=None,
                should_invoke_rag=True,
                resolved_subject_id=intent.subject_id,
            )

    def _log_observability(self, intent: DocumentIntent, route: str) -> None:
        """
        Emits structured logs for debugging and system observability.
        Does NOT log sensitive document content or signed URLs.
        """
        log_payload = {
            "intent": intent.intent,
            "document_type": intent.document_type,
            "subject_id": intent.subject_id,
            "search_query": intent.search_query,
            "retrieval_route": route,
        }
        logger.info(f"Structured Query Route: {json.dumps(log_payload)}")
        print(f"[Observability] {json.dumps(log_payload)}")
