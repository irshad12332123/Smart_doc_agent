import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root and rag are on sys.path
_ROOT_DIR = str(Path(__file__).resolve().parent.parent)
_RAG_DIR = os.path.join(_ROOT_DIR, "rag")
if _RAG_DIR not in sys.path:
    sys.path.insert(0, _RAG_DIR)
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from query_engine.rewrite_query import format_history_context, rewrite_query


class TestRewriteQuery(unittest.TestCase):

    def test_format_history_context_empty_or_none(self):
        self.assertEqual(format_history_context(None), "")
        self.assertEqual(format_history_context([]), "")

    def test_format_history_context_limits_turns(self):
        history = [
            {"role": "user", "content": f"Question {i}"}
            if i % 2 == 1
            else {"role": "assistant", "content": f"Answer {i}"}
            for i in range(1, 20)
        ]
        # max_turns=3 keeps at most 6 messages (3 turns)
        formatted = format_history_context(history, max_turns=3)
        lines = formatted.split("\n")
        self.assertLessEqual(len(lines), 6)
        # Should include recent entries
        self.assertIn("Question 19", formatted)

    def test_format_history_context_truncates_long_messages(self):
        long_text = "A" * 500
        history = [{"role": "user", "content": long_text}]
        formatted = format_history_context(history, max_char_per_message=50)
        self.assertTrue(formatted.startswith("User: " + "A" * 50 + "..."))

    @patch("query_engine.rewrite_query.load_slm")
    def test_rewrite_query_success_with_groq_response(self, mock_load_slm):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Explain ACID properties in relational database management systems"))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_load_slm.return_value = mock_client

        result = rewrite_query("Explain ACID properties", model="test-model")
        self.assertEqual(result, "Explain ACID properties in relational database management systems")

        # Verify chat completion call
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        self.assertEqual(call_kwargs["model"], "test-model")

    @patch("query_engine.rewrite_query.load_slm")
    def test_rewrite_query_strips_quotes(self, mock_load_slm):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='"What are B+ trees?"'))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_load_slm.return_value = mock_client

        result = rewrite_query("What are B+ trees?", model="test-model")
        self.assertEqual(result, "What are B+ trees?")

    @patch("query_engine.rewrite_query.load_slm")
    def test_rewrite_query_with_history_context(self, mock_load_slm):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="How does Docker containerization work?"))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_load_slm.return_value = mock_client

        history = [
            {"role": "user", "content": "Tell me about Docker containerization"},
            {"role": "assistant", "content": "Docker is an open platform for developing, shipping, and running apps."},
        ]

        result = rewrite_query("How does it work?", model="test-model", history=history)
        self.assertEqual(result, "How does Docker containerization work?")

        # Check that history context was included in user prompt
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        user_message_content = call_kwargs["messages"][1]["content"]
        self.assertIn("Recent conversation history:", user_message_content)
        self.assertIn("Docker is an open platform", user_message_content)
        self.assertIn('Latest user query: "How does it work?"', user_message_content)

    @patch("query_engine.rewrite_query.load_slm")
    def test_rewrite_query_without_history(self, mock_load_slm):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="What is Kubernetes?"))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_load_slm.return_value = mock_client

        result = rewrite_query("What is k8s?", model="test-model", history=None)
        self.assertEqual(result, "What is Kubernetes?")

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        user_message_content = call_kwargs["messages"][1]["content"]
        self.assertNotIn("Recent conversation history:", user_message_content)
        self.assertIn('User\'s query: "What is k8s?"', user_message_content)

    @patch("query_engine.rewrite_query.load_slm")
    def test_rewrite_query_fallback_on_exception(self, mock_load_slm):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("Groq API rate limit or network error")
        mock_load_slm.return_value = mock_client

        # Should not raise exception, falls back to original query
        result = rewrite_query("Explain neural networks", model="test-model")
        self.assertEqual(result, "Explain neural networks")

    def test_rewrite_query_empty_query(self):
        self.assertEqual(rewrite_query("", model="test-model"), "")
        self.assertEqual(rewrite_query("   ", model="test-model"), "   ")


if __name__ == "__main__":
    unittest.main()
