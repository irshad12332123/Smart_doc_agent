import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure backend directory, rag, and project root are on sys.path
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent)
_RAG_DIR = os.path.join(_BACKEND_DIR, "rag")
_REPO_DIR = str(Path(__file__).resolve().parent.parent.parent)
for _p in (_RAG_DIR, _BACKEND_DIR, _REPO_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from query_graph import (
    RAGState,
    route_query,
    choose_search,
    deterministic_search,
    after_deterministic,
    rag_search,
    evaluate,
    after_evaluation,
    rewrite_query_node,
    generate,
    query_graph,
    run_query,
)
from intent.schema import DocumentIntent


class TestQueryGraph(unittest.TestCase):

    # 1. Routing node tests
    @patch("query_graph.DocumentRouter")
    def test_route_query_metadata_routes_to_deterministic(self, mock_router_cls):
        mock_router = MagicMock()
        mock_result = MagicMock()
        mock_result.route = "metadata"
        mock_result.should_invoke_rag = False
        mock_result.documents = [{"id": "doc1", "title": "Assignment 1"}]
        mock_result.formatted_text = "Here is Assignment 1"
        mock_result.intent = DocumentIntent(intent="document_listing", document_type="assignment")
        mock_router.route.return_value = mock_result
        mock_router_cls.return_value = mock_router

        state: RAGState = {"query": "List assignments"}
        result = route_query(state)

        self.assertEqual(result["route"], "deterministic")
        self.assertEqual(len(result["chunks"]), 1)
        self.assertEqual(result["formatted_text"], "Here is Assignment 1")
        self.assertEqual(result["attempt_count"], 0)

    @patch("query_graph.DocumentRouter")
    def test_route_query_hybrid_routes_to_rag(self, mock_router_cls):
        mock_router = MagicMock()
        mock_result = MagicMock()
        mock_result.route = "hybrid"
        mock_result.should_invoke_rag = True
        mock_result.documents = []
        mock_result.formatted_text = None
        mock_result.intent = DocumentIntent(intent="normal_rag_query")
        mock_router.route.return_value = mock_result
        mock_router_cls.return_value = mock_router

        state: RAGState = {"query": "What is 3NF in DBMS?"}
        result = route_query(state)

        self.assertEqual(result["route"], "rag")
        self.assertEqual(result["chunks"], [])

    def test_route_query_explicit_route(self):
        state: RAGState = {"query": "Test", "route": "deterministic"}
        result = route_query(state)
        self.assertEqual(result["route"], "deterministic")

    @patch("query_graph.DocumentRouter")
    def test_route_query_exception_fallback(self, mock_router_cls):
        mock_router = MagicMock()
        mock_router.route.side_effect = RuntimeError("Router error")
        mock_router_cls.return_value = mock_router

        state: RAGState = {"query": "Test query"}
        result = route_query(state)
        self.assertEqual(result["route"], "rag")
        self.assertIn("error", result)

    # 2. choose_search edge tests
    def test_choose_search(self):
        self.assertEqual(choose_search({"route": "deterministic"}), "deterministic_search")
        self.assertEqual(choose_search({"route": "metadata"}), "deterministic_search")
        self.assertEqual(choose_search({"route": "rag"}), "rag_search")
        self.assertEqual(choose_search({"route": "hybrid"}), "rag_search")

    # 3. deterministic_search node tests
    def test_deterministic_search_existing_chunks(self):
        chunks = [{"id": "d1", "title": "Doc 1"}]
        result = deterministic_search({"chunks": chunks})
        self.assertEqual(result["chunks"], chunks)

    @patch("query_graph.DocumentService")
    def test_deterministic_search_queries_document_service(self, mock_service_cls):
        mock_service = MagicMock()
        mock_service.lookup_documents.return_value = [{"id": "d1", "title": "Doc 1"}]
        mock_service_cls.return_value = mock_service

        intent = DocumentIntent(intent="document_search", search_query="test")
        result = deterministic_search({"intent": intent})
        self.assertEqual(len(result["chunks"]), 1)
        mock_service.lookup_documents.assert_called_once_with(intent, generate_signed_urls=True)

    # 4. after_deterministic edge tests
    def test_after_deterministic(self):
        self.assertEqual(after_deterministic({"chunks": [{"id": "1"}]}), "evaluate")
        self.assertEqual(after_deterministic({"chunks": []}), "rag_search")
        self.assertEqual(after_deterministic({}), "rag_search")

    # 5. rag_search node tests
    @patch("query_graph.HybridRetriever")
    def test_rag_search_success(self, mock_retriever_cls):
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [
            {"id": "c1", "document_id": "d1", "content": "Sample chunk", "rrf_score": 0.8}
        ]
        mock_retriever_cls.return_value = mock_retriever

        result = rag_search({"query": "Explain transactions"})
        self.assertEqual(len(result["chunks"]), 1)
        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(result["sources"][0]["text"], "Sample chunk")

    # 6. evaluate node tests
    @patch("query_graph.EvidenceEvaluator")
    def test_evaluate_sufficient_evidence(self, mock_evaluator_cls):
        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = {
            "relevance": True,
            "sufficiency": True,
            "quality": True,
            "scores": {"relevance": 0.9, "sufficiency": 0.85, "quality": 0.9},
            "reason": "Good context",
        }
        mock_evaluator_cls.return_value = mock_evaluator

        chunks = [{"content": "Relevant content"}]
        result = evaluate({"original_query": "Explain transactions", "chunks": chunks})
        self.assertTrue(result["sufficient"])
        self.assertEqual(result["evaluation"]["reason"], "Good context")

    @patch("query_graph.EvidenceEvaluator")
    def test_evaluate_metadata_chunks(self, mock_evaluator_cls):
        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = {
            "relevance": True,
            "sufficiency": True,
            "quality": True,
            "scores": {"relevance": 0.95, "sufficiency": 0.9, "quality": 0.9},
            "reason": "Metadata directly matches query",
        }
        mock_evaluator_cls.return_value = mock_evaluator

        chunks = [
            {
                "id": "doc1",
                "title": "DBMS Assignment 1",
                "document_type": "assignment",
                "subject_name": "Database Systems",
                "deadline": "2026-11-01",
            }
        ]
        result = evaluate({"original_query": "Find DBMS assignments", "chunks": chunks})
        self.assertTrue(result["sufficient"])
        self.assertEqual(result["evaluation"]["reason"], "Metadata directly matches query")
        mock_evaluator_cls.assert_called_once()
        call_kwargs = mock_evaluator_cls.call_args[1] if mock_evaluator_cls.call_args[1] else {}
        call_args = mock_evaluator_cls.call_args[0] if mock_evaluator_cls.call_args[0] else ()
        evidence_passed = call_kwargs.get("evidence") or (call_args[1] if len(call_args) > 1 else None)
        self.assertIsNotNone(evidence_passed)
        self.assertIn("Title: DBMS Assignment 1", evidence_passed[0]["text"])
        self.assertIn("Type: assignment", evidence_passed[0]["text"])

    def test_evaluate_empty_chunks(self):
        result = evaluate({"original_query": "Explain transactions", "chunks": []})
        self.assertFalse(result["sufficient"])
        self.assertEqual(result["evaluation"]["reason"], "No evidence retrieved.")

    # 7. after_evaluation edge tests
    def test_after_evaluation(self):
        # Sufficient -> generate
        self.assertEqual(after_evaluation({"sufficient": True, "attempt_count": 0, "max_attempts": 2}), "generate")
        # Insufficient and attempts < max -> rewrite_query
        self.assertEqual(after_evaluation({"sufficient": False, "attempt_count": 0, "max_attempts": 2}), "rewrite_query")
        # Insufficient and attempts >= max -> generate
        self.assertEqual(after_evaluation({"sufficient": False, "attempt_count": 2, "max_attempts": 2}), "generate")

    # 8. rewrite_query_node tests
    @patch("query_graph.rewrite_query")
    def test_rewrite_query_node(self, mock_rewrite):
        mock_rewrite.return_value = "Optimized query for database transactions"
        state: RAGState = {"original_query": "transactions", "attempt_count": 0}

        result = rewrite_query_node(state)
        self.assertEqual(result["query"], "Optimized query for database transactions")
        self.assertEqual(result["attempt_count"], 1)

    @patch("query_graph.rewrite_query")
    @patch("query_graph.GROQ_MODEL", "test-groq-model")
    def test_rewrite_query_node_passes_feedback_and_attempt(self, mock_rewrite):
        mock_rewrite.return_value = "Optimized query for database transactions"
        state: RAGState = {
            "query": "current query",
            "original_query": "initial question",
            "attempt_count": 1,
            "evaluation": {"reason": "Missing transaction ACID definitions"},
        }

        result = rewrite_query_node(state)
        self.assertEqual(result["query"], "Optimized query for database transactions")
        self.assertEqual(result["attempt_count"], 2)
        mock_rewrite.assert_called_once_with(
            query="current query",
            model="test-groq-model",
            history=None,
            feedback="Missing transaction ACID definitions",
            attempt=2,
            original_query="initial question",
        )

    # 9. generate node tests
    def test_generate_formatted_text(self):
        state: RAGState = {"formatted_text": "Pre-formatted documents list"}
        result = generate(state)
        self.assertEqual(result["answer"], "Pre-formatted documents list")

    def test_generate_empty_chunks(self):
        state: RAGState = {"chunks": []}
        result = generate(state)
        self.assertIn("couldn't find relevant passages", result["answer"])

    @patch("query_graph.CallLLM")
    def test_generate_grounded_answer(self, mock_call_llm_cls):
        mock_llm = MagicMock()
        mock_llm.generate_answer.return_value = "Transactions satisfy ACID properties."
        mock_call_llm_cls.return_value = mock_llm

        state: RAGState = {
            "original_query": "What are transactions?",
            "chunks": [{"content": "Transactions in databases..."}],
        }
        result = generate(state)
        self.assertEqual(result["answer"], "Transactions satisfy ACID properties.")

    # 10. End-to-end graph tests
    @patch("query_graph.DocumentRouter")
    @patch("query_graph.EvidenceEvaluator")
    def test_e2e_deterministic_path(self, mock_evaluator_cls, mock_router_cls):
        mock_router = MagicMock()
        mock_result = MagicMock()
        mock_result.route = "metadata"
        mock_result.should_invoke_rag = False
        mock_result.documents = [{"id": "d1", "title": "DBMS Assignment 1"}]
        mock_result.formatted_text = "Here is DBMS Assignment 1"
        mock_result.intent = DocumentIntent(intent="document_listing")
        mock_router.route.return_value = mock_result
        mock_router_cls.return_value = mock_router

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = {
            "relevance": True,
            "sufficiency": True,
            "quality": True,
            "scores": {"relevance": 0.95, "sufficiency": 0.9, "quality": 0.9},
            "reason": "Deterministic documents matched query",
        }
        mock_evaluator_cls.return_value = mock_evaluator

        output = run_query("Show DBMS assignments")
        self.assertEqual(output["route"], "deterministic")
        self.assertTrue(output["sufficient"])
        self.assertEqual(output["answer"], "Here is DBMS Assignment 1")
        mock_evaluator.evaluate.assert_called_once()

    @patch("query_graph.DocumentRouter")
    @patch("query_graph.HybridRetriever")
    @patch("query_graph.EvidenceEvaluator")
    @patch("query_graph.rewrite_query")
    @patch("query_graph.CallLLM")
    def test_e2e_deterministic_insufficient_fallback_to_rag(
        self,
        mock_call_llm_cls,
        mock_rewrite,
        mock_evaluator_cls,
        mock_retriever_cls,
        mock_router_cls,
    ):
        mock_router = MagicMock()
        mock_result = MagicMock()
        mock_result.route = "metadata"
        mock_result.should_invoke_rag = False
        mock_result.documents = [{"id": "d1", "title": "DBMS Assignment 1"}]
        mock_result.formatted_text = "Here is DBMS Assignment 1"
        mock_result.intent = DocumentIntent(intent="document_search", search_query="DBMS Assignment 1 details")
        mock_router.route.return_value = mock_result
        mock_router_cls.return_value = mock_router

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.side_effect = [
            {
                "relevance": True,
                "sufficiency": False,
                "quality": True,
                "scores": {"relevance": 0.8, "sufficiency": 0.2, "quality": 0.8},
                "reason": "Metadata alone does not answer specific question details",
            },
            {
                "relevance": True,
                "sufficiency": True,
                "quality": True,
                "scores": {"relevance": 0.9, "sufficiency": 0.9, "quality": 0.9},
                "reason": "Retrieved chunks contain complete details",
            },
        ]
        mock_evaluator_cls.return_value = mock_evaluator

        mock_rewrite.return_value = "DBMS Assignment 1 detailed specifications"

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [
            {"id": "c1", "content": "Question 1 requires ER diagram modeling."}
        ]
        mock_retriever_cls.return_value = mock_retriever

        mock_llm = MagicMock()
        mock_llm.generate_answer.return_value = "Question 1 requires ER diagram modeling."
        mock_call_llm_cls.return_value = mock_llm

        output = run_query("What does question 1 in DBMS Assignment 1 require?", max_attempts=2)
        self.assertEqual(output["route"], "rag")
        self.assertTrue(output["sufficient"])
        self.assertEqual(output["answer"], "Question 1 requires ER diagram modeling.")
        self.assertEqual(mock_evaluator.evaluate.call_count, 2)

    @patch("query_graph.DocumentRouter")
    @patch("query_graph.HybridRetriever")
    @patch("query_graph.EvidenceEvaluator")
    @patch("query_graph.CallLLM")
    def test_e2e_rag_path_sufficient(
        self, mock_call_llm_cls, mock_evaluator_cls, mock_retriever_cls, mock_router_cls
    ):
        # 1. Router routes to hybrid
        mock_router = MagicMock()
        mock_router_res = MagicMock()
        mock_router_res.route = "hybrid"
        mock_router_res.should_invoke_rag = True
        mock_router_res.documents = []
        mock_router_res.formatted_text = None
        mock_router_res.intent = DocumentIntent(intent="normal_rag_query")
        mock_router.route.return_value = mock_router_res
        mock_router_cls.return_value = mock_router

        # 2. Hybrid retriever returns chunks
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [
            {"id": "c1", "content": "Normalization prevents redundancy."}
        ]
        mock_retriever_cls.return_value = mock_retriever

        # 3. Evidence evaluator deems it sufficient
        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = {
            "relevance": True,
            "sufficiency": True,
            "quality": True,
            "scores": {"relevance": 0.9, "sufficiency": 0.9, "quality": 0.9},
            "reason": "Complete evidence",
        }
        mock_evaluator_cls.return_value = mock_evaluator

        # 4. LLM generates answer
        mock_llm = MagicMock()
        mock_llm.generate_answer.return_value = "Normalization minimizes data duplication."
        mock_call_llm_cls.return_value = mock_llm

        output = run_query("What is normalization?")
        self.assertEqual(output["route"], "rag")
        self.assertTrue(output["sufficient"])
        self.assertEqual(output["answer"], "Normalization minimizes data duplication.")
        self.assertEqual(output["attempt_count"], 0)

    @patch("query_graph.DocumentRouter")
    @patch("query_graph.HybridRetriever")
    @patch("query_graph.EvidenceEvaluator")
    @patch("query_graph.rewrite_query")
    @patch("query_graph.CallLLM")
    def test_e2e_rag_rewrite_loop_then_generate(
        self,
        mock_call_llm_cls,
        mock_rewrite,
        mock_evaluator_cls,
        mock_retriever_cls,
        mock_router_cls,
    ):
        mock_router = MagicMock()
        mock_router_res = MagicMock()
        mock_router_res.route = "hybrid"
        mock_router_res.should_invoke_rag = True
        mock_router_res.documents = []
        mock_router_res.formatted_text = None
        mock_router_res.intent = DocumentIntent(intent="normal_rag_query")
        mock_router.route.return_value = mock_router_res
        mock_router_cls.return_value = mock_router

        mock_retriever = MagicMock()
        mock_retriever.retrieve.side_effect = [
            [{"id": "c1", "content": "Weak context"}],
            [{"id": "c2", "content": "Strong context"}],
        ]
        mock_retriever_cls.return_value = mock_retriever

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.side_effect = [
            {"sufficiency": False, "scores": {}, "reason": "Insufficient"},
            {"sufficiency": True, "scores": {}, "reason": "Good"},
        ]
        mock_evaluator_cls.return_value = mock_evaluator

        mock_rewrite.return_value = "Improved query"

        mock_llm = MagicMock()
        mock_llm.generate_answer.return_value = "Final answer after rewrite."
        mock_call_llm_cls.return_value = mock_llm

        output = run_query("Vague query", max_attempts=2)
        self.assertEqual(output["attempt_count"], 1)
        self.assertTrue(output["sufficient"])
        self.assertEqual(output["answer"], "Final answer after rewrite.")
        mock_rewrite.assert_called_once()

    @patch("query_graph.DocumentRouter")
    @patch("query_graph.DocumentService")
    @patch("query_graph.HybridRetriever")
    @patch("query_graph.EvidenceEvaluator")
    @patch("query_graph.CallLLM")
    def test_e2e_deterministic_fallback_to_rag(
        self,
        mock_call_llm_cls,
        mock_evaluator_cls,
        mock_retriever_cls,
        mock_service_cls,
        mock_router_cls,
    ):
        # Router thinks it might be deterministic
        mock_router = MagicMock()
        mock_router_res = MagicMock()
        mock_router_res.route = "metadata"
        mock_router_res.should_invoke_rag = False
        mock_router_res.documents = []  # No documents found
        mock_router_res.formatted_text = None
        mock_router_res.intent = DocumentIntent(intent="document_search", search_query="rare doc")
        mock_router.route.return_value = mock_router_res
        mock_router_cls.return_value = mock_router

        # DocumentService also returns empty
        mock_service = MagicMock()
        mock_service.lookup_documents.return_value = []
        mock_service_cls.return_value = mock_service

        # Falls back to rag_search
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [{"id": "c1", "content": "Found via hybrid search"}]
        mock_retriever_cls.return_value = mock_retriever

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = {"sufficiency": True, "scores": {}, "reason": "OK"}
        mock_evaluator_cls.return_value = mock_evaluator

        mock_llm = MagicMock()
        mock_llm.generate_answer.return_value = "Answer retrieved via fallback."
        mock_call_llm_cls.return_value = mock_llm

        output = run_query("Find rare doc")
        self.assertEqual(output["answer"], "Answer retrieved via fallback.")

    # 11. Endpoint orchestration tests (POST /api/query and POST /api/chat)
    @patch("ingestion.ingestion.query_graph")
    def test_query_endpoint_success(self, mock_graph):
        from app import create_app
        client = create_app().test_client()

        mock_graph.invoke.return_value = {
            "query": "What is normalization?",
            "original_query": "What is normalization?",
            "route": "rag",
            "answer": "Normalization organizes database fields.",
            "documents": [],
            "sources": [{"chunk_id": "c1", "text": "Normalization info"}],
            "evaluation": {"sufficiency": True},
            "sufficient": True,
            "attempt_count": 0,
        }

        res = client.post(
            "/api/query",
            json={"query": "What is normalization?", "history": []},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["route"], "rag")
        self.assertEqual(data["answer"], "Normalization organizes database fields.")
        self.assertEqual(len(data["sources"]), 1)
        self.assertTrue(data["sufficient"])
        mock_graph.invoke.assert_called_once()

    def test_query_endpoint_validation_error(self):
        from app import create_app
        client = create_app().test_client()

        # Empty query
        res = client.post("/api/query", json={"query": ""})
        self.assertEqual(res.status_code, 400)

        # Invalid history format
        res = client.post("/api/query", json={"query": "valid", "history": "not-a-list"})
        self.assertEqual(res.status_code, 400)

    @patch("ingestion.ingestion.query_graph")
    def test_query_endpoint_internal_error(self, mock_graph):
        from app import create_app
        client = create_app().test_client()

        mock_graph.invoke.side_effect = RuntimeError("Graph execution failed")
        res = client.post("/api/query", json={"query": "test query"})
        self.assertEqual(res.status_code, 500)
        self.assertIn("Query orchestration failed", res.get_json()["detail"])

    @patch("ingestion.ingestion.query_graph")
    def test_chat_endpoint_orchestration_sse(self, mock_graph):
        from app import create_app
        client = create_app().test_client()

        mock_graph.invoke.return_value = {
            "query": "Show DBMS docs",
            "original_query": "Show DBMS docs",
            "route": "deterministic",
            "answer": "Here are the DBMS documents.",
            "documents": [{"id": "d1", "title": "DBMS Notes"}],
            "sources": [],
            "attempt_count": 0,
        }

        res = client.post(
            "/api/chat",
            json={"message": "Show DBMS docs", "history": []},
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/event-stream", res.content_type)
        body = res.get_data(as_text=True)
        self.assertIn('"type": "documents"', body)
        self.assertIn('"type": "token"', body)
        self.assertIn("Here are the DBMS documents.", body)
        self.assertIn('"type": "done"', body)


if __name__ == "__main__":
    unittest.main()
