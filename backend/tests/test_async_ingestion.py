import hashlib
import io
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_BACKEND_DIR = str(Path(__file__).resolve().parent.parent)
_RAG_DIR = os.path.join(_BACKEND_DIR, "rag")
_REPO_DIR = str(Path(__file__).resolve().parent.parent.parent)
for _p in (_RAG_DIR, _BACKEND_DIR, _REPO_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from rag.app import create_app
from ingestion.ingest_repository import (
    create_job,
    get_job,
    update_job,
    find_document_by_hash,
)
from async_engine.tasks import process_ingestion_job, sync_sparse_index_task


class TestAsyncIngestion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_repository_create_get_update_job(self):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        # Mock insert
        mock_table.insert.return_value.execute.return_value.data = [{
            "id": "job-123",
            "s3_key": "notes/test.pdf",
            "file_sha256": "abc123hash",
            "status": "queued",
            "attempts": 0,
            "max_attempts": 5,
        }]

        job = create_job("notes/test.pdf", "abc123hash", supabase_client=mock_client)
        self.assertEqual(job["id"], "job-123")
        self.assertEqual(job["status"], "queued")
        self.assertEqual(job["attempts"], 0)

        # Mock select
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [job]
        fetched = get_job("job-123", supabase_client=mock_client)
        self.assertEqual(fetched["id"], "job-123")

        # Mock update
        mock_table.update.return_value.eq.return_value.execute.return_value.data = [{
            "id": "job-123",
            "status": "processing",
            "attempts": 1,
        }]
        updated = update_job("job-123", supabase_client=mock_client, status="processing", attempts=1)
        self.assertEqual(updated["status"], "processing")

    def test_find_document_by_hash(self):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_table.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{
            "id": "doc-uuid-99",
            "title": "Existing.pdf",
            "hash_key": "existing-hash-sha256",
        }]

        found = find_document_by_hash("existing-hash-sha256", supabase_client=mock_client)
        self.assertIsNotNone(found)
        self.assertEqual(found["id"], "doc-uuid-99")

        # Not found test
        mock_table.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        not_found = find_document_by_hash("new-unique-hash", supabase_client=mock_client)
        self.assertIsNone(not_found)

    @patch("modules.auth.middleware.get_supabase_client")
    @patch("ingestion.ingestion.find_document_by_hash")
    def test_ingest_skips_duplicate_hash(self, mock_find_hash, mock_get_supabase):
        mock_auth_user = MagicMock()
        mock_auth_user.id = "user-123"
        mock_supabase = MagicMock()
        mock_supabase.auth.get_user.return_value.user = mock_auth_user
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "id": "user-123",
            "full_name": "Test User",
            "role": "student",
        }
        mock_get_supabase.return_value = mock_supabase

        mock_find_hash.return_value = {
            "id": "existing-doc-id",
            "title": "syllabus.pdf",
            "hash_key": "hash123",
        }

        data = {
            "files": (io.BytesIO(b"duplicate test content"), "syllabus.pdf"),
            "batch_ids": ["batch-1"],
        }
        res = self.client.post(
            "/api/ingest",
            data=data,
            headers={"Authorization": "Bearer fake-token"},
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertIn("already been ingested", body.get("message", ""))
        self.assertEqual(len(body.get("skipped", [])), 1)
        self.assertEqual(body["skipped"][0]["reason"], "already_exists")
        self.assertEqual(body["skipped"][0]["document_id"], "existing-doc-id")

    @patch("modules.auth.middleware.get_supabase_client")
    @patch("ingestion.ingestion.update_job")
    @patch("ingestion.ingestion.process_ingestion_job.delay")
    @patch("ingestion.ingestion.create_job")
    @patch("ingestion.ingestion.find_document_by_hash")
    @patch("ingestion.ingestion.aws_s3_client.put_object")
    def test_ingest_enqueues_async_job(
        self, mock_s3_put, mock_find_hash, mock_create_job, mock_delay, mock_update_job, mock_get_supabase
    ):
        mock_auth_user = MagicMock()
        mock_auth_user.id = "user-123"
        mock_supabase = MagicMock()
        mock_supabase.auth.get_user.return_value.user = mock_auth_user
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "id": "user-123",
            "full_name": "Test User",
            "role": "student",
        }
        mock_get_supabase.return_value = mock_supabase

        mock_find_hash.return_value = None  # No existing hash
        mock_create_job.return_value = {
            "id": "job-new-123",
            "status": "queued",
            "s3_key": "notes/new_file.pdf",
            "file_sha256": "fake-sha256",
        }
        mock_task = MagicMock()
        mock_task.id = "celery-task-999"
        mock_delay.return_value = mock_task

        data = {
            "files": (io.BytesIO(b"Brand new unique content"), "new_file.pdf"),
            "batch_ids": ["batch-1"],
            "subject_id": "subject-1",
        }
        res = self.client.post(
            "/api/ingest",
            data=data,
            headers={"Authorization": "Bearer fake-token"},
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 202)
        body = res.get_json()
        self.assertEqual(body.get("total_queued"), 1)
        self.assertEqual(body["jobs"][0]["job_id"], "job-new-123")
        self.assertEqual(body["jobs"][0]["task_id"], "celery-task-999")
        self.assertEqual(body["jobs"][0]["status"], "queued")
        mock_delay.assert_called_once()
        mock_update_job.assert_called_with("job-new-123", celery_task_id="celery-task-999")

    @patch("async_engine.tasks.SparseIngestion")
    @patch("async_engine.tasks.DenseIngestion")
    @patch("async_engine.tasks.aws_s3_client.get_object")
    @patch("async_engine.tasks.update_job")
    @patch("async_engine.tasks.get_job")
    def test_process_ingestion_job_task_success(
        self, mock_get_job, mock_update_job, mock_s3_get, mock_dense_cls, mock_sparse_cls
    ):
        mock_get_job.return_value = {
            "id": "job-100",
            "s3_key": "notes/lecture1.pdf",
            "file_sha256": "sha256-lecture-1",
            "attempts": 0,
            "max_attempts": 5,
            "status": "queued",
        }
        mock_s3_get.return_value = {
            "Body": io.BytesIO(b"Mock PDF file content bytes")
        }

        mock_dense_instance = MagicMock()
        mock_dense_cls.return_value = mock_dense_instance
        mock_dense_instance.ingest.return_value = {
            "doc_id": "doc-uuid-777",
            "filename": "lecture1.pdf",
            "filetype": "pdf",
            "num_chunks": 4,
        }

        mock_sparse_instance = MagicMock()
        mock_sparse_cls.return_value = mock_sparse_instance
        mock_sparse_instance.regenerate_index.return_value = {
            "total_chunks": 10,
            "status": "ready",
        }

        result = process_ingestion_job.run(
            job_id="job-100",
            subject_id="sub-1",
            batch_ids=["b-1"],
            filename="lecture1.pdf",
            uploaded_by="user-1",
        )

        self.assertEqual(result["document_id"], "doc-uuid-777")
        self.assertEqual(result["dense"]["num_chunks"], 4)
        self.assertEqual(result["sparse"]["status"], "ready")

        # Verify dense ingestion called with hash_key
        mock_dense_instance.ingest.assert_called_once_with(
            subject_id="sub-1",
            batch_ids=["b-1"],
            extension="pdf",
            filename="lecture1.pdf",
            s3_key="notes/lecture1.pdf",
            file_bytes=b"Mock PDF file content bytes",
            uploaded_by="user-1",
            hash_key="sha256-lecture-1",
        )

        # Verify sparse ingestion was called after dense ingestion
        mock_sparse_instance.regenerate_index.assert_called_once()

        # Check update_job completed call
        completed_call = [
            call for call in mock_update_job.call_args_list
            if call.kwargs.get("status") == "completed"
        ]
        self.assertTrue(len(completed_call) > 0)
        self.assertEqual(completed_call[0].kwargs["result"]["document_id"], "doc-uuid-777")

    @patch("async_engine.tasks.sync_sparse_index_task.delay")
    def test_sync_index_async_route(self, mock_delay):
        mock_task = MagicMock()
        mock_task.id = "sparse-sync-task-123"
        mock_delay.return_value = mock_task

        res = self.client.post("/api/index/sync")
        self.assertEqual(res.status_code, 202)
        body = res.get_json()
        self.assertEqual(body.get("status"), "queued")
        self.assertEqual(body.get("task_id"), "sparse-sync-task-123")
        mock_delay.assert_called_once()

    @patch("ingestion.ingestion.get_job")
    def test_get_job_status_route(self, mock_get_job):
        mock_get_job.return_value = {
            "id": "job-status-1",
            "status": "completed",
            "document_id": "doc-uuid-123",
            "attempts": 1,
            "max_attempts": 5,
        }
        res = self.client.get("/api/jobs/job-status-1")
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertEqual(body["job"]["status"], "completed")
        self.assertEqual(body["job"]["document_id"], "doc-uuid-123")


if __name__ == "__main__":
    unittest.main()
