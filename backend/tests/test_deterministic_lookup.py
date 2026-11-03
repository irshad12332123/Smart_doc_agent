import json
import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure backend directory, rag, and project root are on sys.path
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent)
_RAG_DIR = os.path.join(_BACKEND_DIR, "rag")
_REPO_DIR = str(Path(__file__).resolve().parent.parent.parent)
for _p in (_RAG_DIR, _BACKEND_DIR, _REPO_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from intent.schema import DocumentIntent, SubjectContext, DeadlineFilter, TimeFilter
from intent.extractor import IntentExtractor
from s3.service import S3Service
from documents.repository import DocumentRepository
from documents.service import DocumentService
from query_engine.router import DocumentRouter, RouterResult


class TestDeterministicLookup(unittest.TestCase):

    def setUp(self):
        self.ref_time = datetime(2026, 10, 5, 12, 0, 0, tzinfo=timezone.utc)
        self.subjects = [
            SubjectContext(id="uuid-dbms-1", name="Database Management System", code="BCS-301"),
            SubjectContext(id="uuid-os-2", name="Operating Systems", code="BCS-302"),
            SubjectContext(id="uuid-cn-3", name="Computer Networks", code="BCS-303"),
            SubjectContext(id="uuid-adbms-4", name="Advanced Database Systems", code="BCS-401"),
        ]
        self.valid_subject_ids = {s.id for s in self.subjects}

    # 1. "Give me all assignments for DBMS"
    def test_give_me_all_assignments_for_dbms(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "intent": "document_listing",
                "document_type": "assignment",
                "subject_id": "uuid-dbms-1",
                "search_query": None,
                "deadline_filter": None,
                "time_filter": None,
                "limit": 20,
            })))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        extractor = IntentExtractor(client=mock_client)
        intent = extractor.extract(
            query="Give me all assignments for DBMS",
            subject_list=self.subjects,
            reference_time=self.ref_time,
        )

        self.assertEqual(intent.intent, "document_listing")
        self.assertEqual(intent.document_type, "assignment")
        self.assertEqual(intent.subject_id, "uuid-dbms-1")
        self.assertIsNone(intent.search_query)

    # 2. "Show DBMS assignments"
    def test_show_dbms_assignments(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "intent": "document_listing",
                "document_type": "assignment",
                "subject_id": "uuid-dbms-1",
                "search_query": None,
                "deadline_filter": None,
                "time_filter": None,
                "limit": 20,
            })))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        extractor = IntentExtractor(client=mock_client)
        intent = extractor.extract(
            query="Show DBMS assignments",
            subject_list=self.subjects,
            reference_time=self.ref_time,
        )

        self.assertEqual(intent.intent, "document_listing")
        self.assertEqual(intent.document_type, "assignment")
        self.assertEqual(intent.subject_id, "uuid-dbms-1")

    # 3. "Give me OS notices"
    def test_give_me_os_notices(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "intent": "document_listing",
                "document_type": "notice",
                "subject_id": "uuid-os-2",
                "search_query": None,
                "deadline_filter": None,
                "time_filter": None,
                "limit": 20,
            })))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        extractor = IntentExtractor(client=mock_client)
        intent = extractor.extract(
            query="Give me OS notices",
            subject_list=self.subjects,
            reference_time=self.ref_time,
        )

        self.assertEqual(intent.intent, "document_listing")
        self.assertEqual(intent.document_type, "notice")
        self.assertEqual(intent.subject_id, "uuid-os-2")

    # 4. "Find the notice about mid semester exam"
    def test_find_notice_about_mid_semester_exam(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "intent": "document_search",
                "document_type": "notice",
                "subject_id": None,
                "search_query": "mid semester exam",
                "deadline_filter": None,
                "time_filter": None,
                "limit": 20,
            })))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        extractor = IntentExtractor(client=mock_client)
        intent = extractor.extract(
            query="Find the notice about mid semester exam",
            subject_list=self.subjects,
            reference_time=self.ref_time,
        )

        self.assertEqual(intent.intent, "document_search")
        self.assertEqual(intent.document_type, "notice")
        self.assertIsNone(intent.subject_id)
        self.assertEqual(intent.search_query, "mid semester exam")

    # 5. "Find DBMS assignment 2"
    def test_find_dbms_assignment_2(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "intent": "document_search",
                "document_type": "assignment",
                "subject_id": "uuid-dbms-1",
                "search_query": "assignment 2",
                "deadline_filter": None,
                "time_filter": None,
                "limit": 20,
            })))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        extractor = IntentExtractor(client=mock_client)
        intent = extractor.extract(
            query="Find DBMS assignment 2",
            subject_list=self.subjects,
            reference_time=self.ref_time,
        )

        self.assertEqual(intent.intent, "document_search")
        self.assertEqual(intent.document_type, "assignment")
        self.assertEqual(intent.subject_id, "uuid-dbms-1")
        self.assertEqual(intent.search_query, "assignment 2")

    # 6. "What is normalization in DBMS?"
    def test_what_is_normalization_in_dbms(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "intent": "normal_rag_query",
                "document_type": None,
                "subject_id": "uuid-dbms-1",
                "search_query": "normalization",
                "deadline_filter": None,
                "time_filter": None,
                "limit": 20,
            })))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        extractor = IntentExtractor(client=mock_client)
        intent = extractor.extract(
            query="What is normalization in DBMS?",
            subject_list=self.subjects,
            reference_time=self.ref_time,
        )

        self.assertEqual(intent.intent, "normal_rag_query")
        self.assertEqual(intent.subject_id, "uuid-dbms-1")

    # 7. Unknown subject
    def test_unknown_subject(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        # SLM tries to invent or returns an unknown subject ID
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "intent": "document_listing",
                "document_type": "assignment",
                "subject_id": "uuid-hallucinated-chemistry",
                "search_query": None,
                "deadline_filter": None,
                "time_filter": None,
                "limit": 20,
            })))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        extractor = IntentExtractor(client=mock_client)
        intent = extractor.extract(
            query="Give me assignments for Organic Chemistry",
            subject_list=self.subjects,  # Chemistry not in enrolled subjects
            reference_time=self.ref_time,
        )

        # Validation MUST strip the un-enrolled / hallucinated subject_id
        self.assertIsNone(intent.subject_id)

    # 8. Ambiguous subject
    def test_ambiguous_subject(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        # SLM correctly flags ambiguous reference between DBMS and Advanced DBMS
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "intent": "document_listing",
                "document_type": "assignment",
                "subject_id": None,
                "search_query": "database",
                "deadline_filter": None,
                "time_filter": None,
                "limit": 20,
            })))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        extractor = IntentExtractor(client=mock_client)
        intent = extractor.extract(
            query="Give me database assignments",
            subject_list=self.subjects,
            reference_time=self.ref_time,
        )

        self.assertEqual(intent.intent, "document_listing")
        self.assertIsNone(intent.subject_id)
        self.assertEqual(intent.search_query, "database")

    # 9. No matching documents
    def test_no_matching_documents(self):
        mock_repo = MagicMock()
        mock_repo.get_documents_by_filters.return_value = []
        doc_service = DocumentService(repository=mock_repo)

        intent = DocumentIntent(
            intent="document_listing",
            document_type="assignment",
            subject_id="uuid-dbms-1",
            search_query=None,
        )

        docs = doc_service.lookup_documents(intent)
        self.assertEqual(len(docs), 0)

        router = DocumentRouter(document_service=doc_service)
        result = router._format_document_list(docs, intent, subject_name="Database Management System")
        self.assertIn("couldn't find any assignments for **Database Management System**", result)

    # 10. Invalid SLM output
    def test_invalid_slm_output_fallback(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        # Malformed / non-JSON response from SLM
        mock_response.choices = [
            MagicMock(message=MagicMock(content="I am an LLM and this is not JSON!"))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        extractor = IntentExtractor(client=mock_client)
        intent = extractor.extract(
            query="Find DBMS assignment 2",
            subject_list=self.subjects,
            reference_time=self.ref_time,
        )

        # Fallback MUST be normal_rag_query without crashing
        self.assertEqual(intent.intent, "normal_rag_query")

    # 11. User attempts to reference unauthorized subject
    def test_unauthorized_subject_security_validation(self):
        # User only has OS enrolled
        user_authorized_subjects = [
            SubjectContext(id="uuid-os-2", name="Operating Systems", code="BCS-302")
        ]

        raw_intent = {
            "intent": "document_listing",
            "document_type": "assignment",
            "subject_id": "uuid-dbms-1",  # User is not enrolled in DBMS
            "search_query": None,
        }

        extractor = IntentExtractor()
        sanitized = extractor.validate_and_sanitize(
            raw_intent=raw_intent,
            valid_subject_ids={s.id for s in user_authorized_subjects},
            reference_time=self.ref_time,
        )

        self.assertIsNone(sanitized.subject_id)

    # 12. Document exists in DB but S3 object is unavailable
    def test_document_exists_in_db_but_s3_unavailable(self):
        mock_repo = MagicMock()
        mock_repo.get_documents_by_filters.return_value = [
            {
                "id": "doc-uuid-1",
                "title": "DBMS Assignment 1.pdf",
                "description": "ER modeling questions",
                "document_type": "assignment",
                "subject_id": "uuid-dbms-1",
                "s3_key": "assignments/non_existent_key.pdf",
                "mime_type": "application/pdf",
                "deadline": "2026-10-15T23:59:59Z",
                "created_at": "2026-10-01T10:00:00Z",
                "updated_at": "2026-10-01T10:00:00Z",
            }
        ]

        mock_s3_service = MagicMock()
        # S3 generation raises exception or returns None
        mock_s3_service.generate_presigned_url.return_value = None

        doc_service = DocumentService(repository=mock_repo, s3_service=mock_s3_service)

        intent = DocumentIntent(
            intent="document_listing",
            document_type="assignment",
            subject_id="uuid-dbms-1",
        )

        docs = doc_service.lookup_documents(intent)
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["title"], "DBMS Assignment 1.pdf")
        self.assertIsNone(docs[0]["file_url"])  # Graceful fallback: URL is None, doc metadata retained

    # 13. Temporal filter resolution
    def test_temporal_filter_resolution(self):
        extractor = IntentExtractor()

        # Yesterday
        y_start, y_end = extractor.compute_time_range("yesterday", self.ref_time)
        self.assertEqual(y_start, "2026-10-04T00:00:00+00:00")
        self.assertEqual(y_end, "2026-10-04T23:59:59.999999+00:00")

        # Today
        t_start, t_end = extractor.compute_time_range("today", self.ref_time)
        self.assertEqual(t_start, "2026-10-05T00:00:00+00:00")
        self.assertEqual(t_end, "2026-10-05T23:59:59.999999+00:00")

        # Last 7 days
        l7_start, l7_end = extractor.compute_time_range("last_7_days", self.ref_time)
        self.assertEqual(l7_start, "2026-09-28T12:00:00+00:00")
        self.assertEqual(l7_end, "2026-10-05T12:00:00+00:00")

    # 14. Document Search Fallback to Hybrid RAG when 0 metadata matches
    def test_document_search_fallback_to_hybrid(self):
        mock_extractor = MagicMock()
        mock_extractor.normalize_subjects.return_value = self.subjects
        mock_extractor.extract.return_value = DocumentIntent(
            intent="document_search",
            document_type="assignment",
            subject_id="uuid-dbms-1",
            search_query="non-existent assignment 99",
        )

        mock_doc_service = MagicMock()
        mock_doc_service.lookup_documents.return_value = []  # 0 metadata matches

        router = DocumentRouter(
            intent_extractor=mock_extractor,
            document_service=mock_doc_service,
        )

        result = router.route(
            query="Find DBMS assignment 99",
            subject_list=self.subjects,
        )

        self.assertEqual(result.route, "hybrid")
        self.assertTrue(result.should_invoke_rag)
        self.assertEqual(result.resolved_subject_id, "uuid-dbms-1")

    # 15. Document Search Metadata Success (no vector search needed)
    def test_document_search_metadata_success(self):
        mock_extractor = MagicMock()
        mock_extractor.normalize_subjects.return_value = self.subjects
        mock_extractor.extract.return_value = DocumentIntent(
            intent="document_search",
            document_type="assignment",
            subject_id="uuid-dbms-1",
            search_query="assignment 2",
        )

        mock_doc_service = MagicMock()
        mock_doc_service.lookup_documents.return_value = [
            {
                "id": "doc-uuid-2",
                "title": "DBMS Assignment 2.pdf",
                "description": "Relational algebra and SQL queries",
                "document_type": "assignment",
                "subject_id": "uuid-dbms-1",
                "s3_key": "assignments/dbms_a2.pdf",
                "file_url": "https://s3.amazonaws.com/test-bucket/signed-url-a2",
            }
        ]

        router = DocumentRouter(
            intent_extractor=mock_extractor,
            document_service=mock_doc_service,
        )

        result = router.route(
            query="Find DBMS assignment 2",
            subject_list=self.subjects,
        )

        self.assertEqual(result.route, "metadata")
        self.assertFalse(result.should_invoke_rag)
        self.assertEqual(len(result.documents), 1)
        self.assertIn("DBMS Assignment 2.pdf", result.formatted_text)

    # 16. Ingestion Metadata Model: unit extraction & flexible future columns
    def test_document_metadata_model_unit_and_flexibility(self):
        from services.ingestion.constants import DocumentMetaData

        # Direct int
        m1 = DocumentMetaData(description="Unit 2 Notes", document_type="notes", unit=2)
        self.assertEqual(m1.unit, 2)
        self.assertEqual(m1.model_dump()["unit"], 2)

        # String format "Unit 3"
        m2 = DocumentMetaData(description="Unit 3 Notes", document_type="notes", unit="Unit 3")
        self.assertEqual(m2.unit, 3)

        # String format "2"
        m3 = DocumentMetaData(description="Unit 2 Notes", document_type="notes", unit="2")
        self.assertEqual(m3.unit, 2)

        # None / "none"
        m4 = DocumentMetaData(description="General Notice", document_type="notice", unit="none")
        self.assertIsNone(m4.unit)

        # Extensibility: extra future columns allowed seamlessly
        m5 = DocumentMetaData(
            description="DBMS unit 4",
            document_type="notes",
            unit=4,
            semester=5,
            academic_year=2026,
        )
        self.assertEqual(m5.unit, 4)
        dump = m5.model_dump()
        self.assertEqual(dump["unit"], 4)
        self.assertEqual(dump["semester"], 5)
        self.assertEqual(dump["academic_year"], 2026)

    # 17. Dense Ingestion pushes unit metadata to Supabase documents table
    @patch("services.ingestion.dense.PdfReader")
    def test_dense_ingestion_pushes_unit_to_documents_table(self, mock_pdf):
        from services.ingestion.dense import DenseIngestion
        from services.ingestion.constants import DocumentMetaData

        mock_client = MagicMock()
        dense = DenseIngestion(client=mock_client)

        meta = DocumentMetaData(
            description="Unit 2 Relational Algebra Notes",
            document_type="notes",
            deadline=None,
            unit=2,
        )

        with patch.object(dense, "_get_file_context_meta_data_from_slm", return_value=meta), \
             patch.object(dense, "_insert_document", return_value="doc-unit-2") as mock_insert, \
             patch.object(dense, "_upload_doc_id_per_batches"), \
             patch.object(dense, "_ingest_bytes", return_value=5):

            res = dense.ingest(
                context_meta_data_generator=MagicMock(),
                subject_id="uuid-dbms-1",
                filename="unit_2_notes.pdf",
                file_bytes=b"%PDF-1.4 mock content",
                s3_key="notes/unit_2_notes.pdf",
            )

            self.assertEqual(res["doc_id"], "doc-unit-2")
            mock_insert.assert_called_once()
            insert_payload = mock_insert.call_args[0][0]
            self.assertEqual(insert_payload["unit"], 2)
            self.assertEqual(insert_payload["document_type"], "notes")
            self.assertEqual(insert_payload["subject_id"], "uuid-dbms-1")
            self.assertEqual(insert_payload["title"], "unit_2_notes.pdf")

    # 18. SLM extracts unit metadata from user query without search_query FTS term
    def test_slm_extracts_unit_metadata_without_search_query(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "intent": "document_listing",
                "document_type": "notes",
                "subject_id": "uuid-dbms-1",
                "unit": 2,
                "search_query": None,
                "deadline_filter": None,
                "time_filter": None,
                "limit": 20,
            })))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        extractor = IntentExtractor(client=mock_client)
        intent = extractor.extract(
            query="give notes of unit 2 for DBMS",
            subject_list=self.subjects,
            reference_time=self.ref_time,
        )

        self.assertEqual(intent.intent, "document_listing")
        self.assertEqual(intent.document_type, "notes")
        self.assertEqual(intent.subject_id, "uuid-dbms-1")
        self.assertEqual(intent.unit, 2)
        self.assertIsNone(intent.search_query)

    # 19. Extractor normalizes legacy "unit X" in search_query to unit metadata
    def test_extractor_normalizes_unit_search_query_into_unit_field(self):
        raw_intent = {
            "intent": "document_search",
            "document_type": "notes",
            "subject_id": "uuid-dbms-1",
            "unit": None,
            "search_query": "unit 4",
        }

        extractor = IntentExtractor()
        sanitized = extractor.validate_and_sanitize(
            raw_intent=raw_intent,
            valid_subject_ids=self.valid_subject_ids,
            reference_time=self.ref_time,
        )

        self.assertEqual(sanitized.unit, 4)
        self.assertIsNone(sanitized.search_query)

    # 20. Repository passes unit to RPC get_documents_by_filters
    def test_repository_passes_unit_to_rpc(self):
        mock_client = MagicMock()
        mock_client.rpc.return_value.execute.return_value.data = [
            {"id": "doc-unit-1", "title": "DBMS Unit 1.pdf", "unit": 1}
        ]
        repo = DocumentRepository(client=mock_client)

        docs = repo.get_documents_by_filters(
            subject_id="uuid-dbms-1",
            unit=1,
            search_query=None,
        )

        self.assertEqual(len(docs), 1)
        mock_client.rpc.assert_called_once()
        rpc_call_name = mock_client.rpc.call_args[0][0]
        rpc_params = mock_client.rpc.call_args[0][1]
        self.assertEqual(rpc_call_name, "get_documents_by_filters")
        self.assertEqual(rpc_params.get("p_unit"), 1)
        self.assertEqual(rpc_params.get("p_subject_id"), "uuid-dbms-1")
        self.assertNotIn("p_search_query", rpc_params)  # None is cleaned out

    # 21. Repository fallback query filters by unit and supports future column filters
    def test_repository_fallback_unit_and_extensible_filters(self):
        mock_client = MagicMock()
        # Force RPC failure to trigger table query fallback
        mock_client.rpc.side_effect = Exception("RPC not found")

        mock_query = MagicMock()
        mock_client.table.return_value.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value.data = [
            {
                "id": "doc-unit-2",
                "title": "DBMS Unit 2.pdf",
                "description": "SQL & Normalization",
                "document_type": "notes",
                "unit": 2,
                "semester": 4,
                "subjects": {"name": "Database Management System", "subject_code": "BCS-301"},
            }
        ]

        repo = DocumentRepository(client=mock_client)
        docs = repo.get_documents_by_filters(
            subject_id="uuid-dbms-1",
            unit=2,
            search_query=None,
            semester=4,  # future extensible column!
        )

        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["unit"], 2)
        self.assertEqual(docs[0]["subject_name"], "Database Management System")
        self.assertEqual(docs[0]["semester"], 4)

        # Verify unit filter was applied with eq
        mock_query.eq.assert_any_call("subject_id", "uuid-dbms-1")
        mock_query.eq.assert_any_call("unit", 2)
        mock_query.eq.assert_any_call("semester", 4)
        # Verify title FTS / or_ was NOT called
        mock_query.or_.assert_not_called()

    # 22. DocumentService formats retrieved docs with unit and future metadata
    def test_document_service_includes_unit_in_processed_docs(self):
        mock_repo = MagicMock()
        mock_repo.get_documents_by_filters.return_value = [
            {
                "id": "doc-u2",
                "title": "DBMS Unit 2 Notes.pdf",
                "description": "Relational Calculus",
                "document_type": "notes",
                "unit": 2,
                "subject_id": "uuid-dbms-1",
                "subject_name": "Database Management System",
                "s3_key": "notes/dbms_u2.pdf",
                "mime_type": "application/pdf",
                "custom_column": "custom_value",
            }
        ]
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = "https://s3.example.com/dbms_u2.pdf"

        service = DocumentService(repository=mock_repo, s3_service=mock_s3)
        intent = DocumentIntent(
            intent="document_listing",
            document_type="notes",
            subject_id="uuid-dbms-1",
            unit=2,
        )

        docs = service.lookup_documents(intent)
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["unit"], 2)
        self.assertEqual(docs[0]["custom_column"], "custom_value")
        self.assertEqual(docs[0]["file_url"], "https://s3.example.com/dbms_u2.pdf")

        # Verify repository was invoked with unit=2
        mock_repo.get_documents_by_filters.assert_called_once()
        call_kwargs = mock_repo.get_documents_by_filters.call_args[1]
        self.assertEqual(call_kwargs.get("unit"), 2)

    # 23. Router formats document list with Unit headers
    def test_router_formats_unit_in_document_list(self):
        router = DocumentRouter()
        intent = DocumentIntent(
            intent="document_listing",
            document_type="notes",
            subject_id="uuid-dbms-1",
            unit=2,
        )
        docs = [
            {
                "id": "doc-1",
                "title": "DBMS Unit 2 Notes.pdf",
                "unit": 2,
                "description": "Transactions and Concurrency",
                "file_url": "https://example.com/unit2.pdf",
            }
        ]

        formatted = router._format_document_list(docs, intent, subject_name="DBMS")
        self.assertIn("Here are the notes for **DBMS** (Unit 2)", formatted)
        self.assertIn("- **Unit:** 2", formatted)
        self.assertIn("DBMS Unit 2 Notes.pdf", formatted)
        self.assertIn("[📥 Download / View File](https://example.com/unit2.pdf)", formatted)

    # 24. Router handles empty unit results with informative message
    def test_router_formats_empty_unit_result(self):
        router = DocumentRouter()
        intent = DocumentIntent(
            intent="document_listing",
            document_type="notes",
            subject_id="uuid-dbms-1",
            unit=5,
        )
        formatted = router._format_document_list([], intent, subject_name="DBMS")
        self.assertEqual(formatted, "I couldn't find any notes for **DBMS** (Unit 5) in your records.")



if __name__ == "__main__":
    unittest.main()
