import json
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

from evaluator.evidence_evaluator import EvidenceEvaluator


class TestEvidenceEvaluator(unittest.TestCase):

    @patch("evaluator.evidence_evaluator.load_slm")
    def test_evaluate_empty_evidence(self, mock_load_slm):
        mock_client = MagicMock()
        mock_load_slm.return_value = mock_client

        evaluator = EvidenceEvaluator(query="give notes of unit 2", evidence=[])
        result = evaluator.evaluate()

        self.assertFalse(result["relevance"])
        self.assertFalse(result["sufficiency"])
        self.assertFalse(result["quality"])
        self.assertFalse(result["extra_info_required"])
        self.assertEqual(result["reason"], "No evidence retrieved.")
        mock_client.chat.completions.create.assert_not_called()

    @patch("evaluator.evidence_evaluator.load_slm")
    def test_evaluate_sufficient_evidence(self, mock_load_slm):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "relevance_score": 0.9,
                        "sufficiency_score": 0.85,
                        "quality_score": 0.8,
                        "extra_info_required": False,
                        "reason": "Evidence thoroughly covers database transactions.",
                    })
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_load_slm.return_value = mock_client

        evidence = [{"text": "DBMS unit 2 covers transactions and recovery."}]
        evaluator = EvidenceEvaluator(query="What is a transaction in DBMS?", evidence=evidence)
        result = evaluator.evaluate()

        self.assertTrue(result["relevance"])
        self.assertTrue(result["sufficiency"])
        self.assertTrue(result["quality"])
        self.assertFalse(result["extra_info_required"])
        self.assertEqual(result["scores"]["relevance"], 0.9)
        self.assertEqual(result["scores"]["sufficiency"], 0.85)

    @patch("evaluator.evidence_evaluator.load_slm")
    def test_evaluate_insufficient_query_extra_info_required(self, mock_load_slm):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "relevance_score": 0.4,
                        "sufficiency_score": 0.2,
                        "quality_score": 0.7,
                        "extra_info_required": True,
                        "reason": "The query asks for notes of unit 2 without specifying the subject.",
                    })
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_load_slm.return_value = mock_client

        evidence = [{"text": "Unit 2 notes for operating systems and database systems."}]
        evaluator = EvidenceEvaluator(query="give notes of unit 2", evidence=evidence)
        result = evaluator.evaluate()

        self.assertFalse(result["relevance"])
        self.assertFalse(result["sufficiency"])
        self.assertTrue(result["quality"])
        self.assertTrue(result["extra_info_required"])
        self.assertIn("without specifying the subject", result["reason"])

    @patch("evaluator.evidence_evaluator.load_slm")
    def test_evaluate_needs_more_context_alias(self, mock_load_slm):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "relevance_score": 0.5,
                        "sufficiency_score": 0.3,
                        "quality_score": 0.7,
                        "needs_more_context": True,
                        "reason": "Missing subject context.",
                    })
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_load_slm.return_value = mock_client

        evidence = [{"text": "Some text"}]
        evaluator = EvidenceEvaluator(query="unit 2", evidence=evidence)
        result = evaluator.evaluate()

        self.assertTrue(result["extra_info_required"])

    @patch("evaluator.evidence_evaluator.load_slm")
    def test_evaluate_invalid_json_fallback(self, mock_load_slm):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Invalid non-json response"))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_load_slm.return_value = mock_client

        evidence = [{"text": "Some text"}]
        evaluator = EvidenceEvaluator(query="test", evidence=evidence)
        result = evaluator.evaluate()

        self.assertFalse(result["relevance"])
        self.assertFalse(result["sufficiency"])
        self.assertFalse(result["quality"])
        self.assertFalse(result["extra_info_required"])
        self.assertIsNone(result["scores"])
        self.assertEqual(result["reason"], "Evaluation response was invalid.")

    @patch("evaluator.evidence_evaluator.load_slm")
    def test_evaluate_out_of_bounds_scores(self, mock_load_slm):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "relevance_score": 1.5,
                        "sufficiency_score": 0.5,
                        "quality_score": 0.5,
                    })
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_load_slm.return_value = mock_client

        evidence = [{"text": "Some text"}]
        evaluator = EvidenceEvaluator(query="test", evidence=evidence)
        result = evaluator.evaluate()

        self.assertFalse(result["sufficiency"])
        self.assertFalse(result["extra_info_required"])
        self.assertEqual(result["reason"], "Evaluation response was invalid.")


if __name__ == "__main__":
    unittest.main()
