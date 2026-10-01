"""
Comprehensive RAG Retrieval Evaluator.

Evaluates and compares:
1. DENSE Retrieval (SentenceTransformers embeddings + Cosine Similarity)
2. SPARSE Retrieval (BM25S + PyStemmer)
3. HYBRID Retrieval (Dense + BM25S fused via Reciprocal Rank Fusion - RRF)
4. HYBRID + CROSS-ENCODER (RRF Fusion + Cross-Encoder Deep Re-ranking)

Metrics Evaluated:
- Hit Rate @ 1, 3, 5
- Recall @ 1, 3, 5
- Precision @ 1, 3, 5
- MRR (Mean Reciprocal Rank)
- MAP (Mean Average Precision)
- NDCG @ 3, 5
- Average Latency (ms)
"""

import json
import logging
import math
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

# Ensure the rag root directory is on sys.path so modules like embedder, services, evaluation, etc. resolve properly
_RAG_DIR = str(Path(__file__).resolve().parent.parent)
if _RAG_DIR not in sys.path:
    sys.path.insert(0, _RAG_DIR)

import bm25s
import numpy as np
import Stemmer

from embedder.embedding import Embedder
from evaluation.dataset import (
    COLLEGE_EVALUATION_QUERIES,
    get_flattened_chunks,
)

from evaluation.metrics import calculate_query_metrics
from services.fusion.rrf import RRFEngine
from services.reranker.cross_encoder import CrossEncoderReranker

logger = logging.getLogger(__name__)


class BenchmarkIndexHarness:
    """
    In-memory / local test index harness for reproducible benchmarking
    across Dense, Sparse, Hybrid, and Cross-Encoder retrievers.
    """

    def __init__(self, chunks: list[dict[str, Any]]):
        self.chunks = chunks
        self.stemmer = Stemmer.Stemmer("english")
        self.embedder = Embedder()
        self.rrf_engine = RRFEngine(k=60)
        self.reranker = CrossEncoderReranker()

        self._build_dense_index()
        self._build_sparse_index()

    def _build_dense_index(self):
        logger.info(f"Generating dense embeddings for {len(self.chunks)} test chunks...")
        corpus_texts = [chunk["content"] for chunk in self.chunks]
        self.embeddings = np.array(self.embedder.generate_embeddings(corpus_texts), dtype=np.float32)
        # Normalize embeddings for fast cosine similarity dot product
        norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.normed_embeddings = self.embeddings / norms

    def _build_sparse_index(self):
        logger.info(f"Building BM25S index for {len(self.chunks)} test chunks...")
        corpus_texts = [chunk["content"] for chunk in self.chunks]
        self.corpus_tokens = bm25s.tokenize(
            corpus_texts,
            stopwords="en",
            stemmer=self.stemmer,
            show_progress=False,
        )
        self.bm25_retriever = bm25s.BM25()
        self.bm25_retriever.index(self.corpus_tokens, show_progress=False)

    def retrieve_dense(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """Dense embedding similarity retrieval."""
        query_emb = np.array(self.embedder.generate_embeddings([query])[0], dtype=np.float32)
        norm = np.linalg.norm(query_emb)
        if norm > 0:
            query_emb = query_emb / norm

        # Cosine similarity dot product
        sims = np.dot(self.normed_embeddings, query_emb)
        top_indices = np.argsort(sims)[::-1][: min(top_k, len(self.chunks))]

        results: list[dict[str, Any]] = []
        for idx in top_indices:
            chunk = dict(self.chunks[idx])
            sim = float(sims[idx])
            chunk["score"] = sim
            chunk["similarity"] = sim
            results.append(chunk)
        return results

    def retrieve_sparse(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """BM25S lexical retrieval."""
        query_tokens = bm25s.tokenize(
            [query],
            stemmer=self.stemmer,
            stopwords="en",
            show_progress=False,
        )
        k = min(top_k, len(self.chunks))
        doc_indices, scores = self.bm25_retriever.retrieve(
            query_tokens,
            k=k,
            show_progress=False,
        )

        results: list[dict[str, Any]] = []
        for idx, score in zip(doc_indices[0], scores[0]):
            chunk = dict(self.chunks[int(idx)])
            chunk["score"] = float(score)
            chunk["similarity"] = float(score)
            results.append(chunk)
        return results

    def retrieve_hybrid_rrf(
        self,
        query: str,
        top_k: int = 10,
        dense_k: int = 15,
        sparse_k: int = 15,
    ) -> list[dict[str, Any]]:
        """Hybrid retrieval combining Dense + BM25S using RRF."""
        dense_results = self.retrieve_dense(query, top_k=dense_k)
        sparse_results = self.retrieve_sparse(query, top_k=sparse_k)
        fused = self.rrf_engine.fuse([dense_results, sparse_results])
        return fused[:top_k]

    def retrieve_hybrid_cross_encoder(
        self,
        query: str,
        top_k: int = 5,
        candidate_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Hybrid RRF candidate retrieval followed by Cross-Encoder deep re-ranking."""
        fused_candidates = self.retrieve_hybrid_rrf(query, top_k=candidate_k)
        reranked = self.reranker.rerank(query, fused_candidates, top_k=top_k)
        return reranked


class RetrievalEvaluator:
    """Runs evaluation benchmark across all retrieval methods and computes metrics."""

    def __init__(self, harness: Optional[BenchmarkIndexHarness] = None):
        chunks = get_flattened_chunks()
        self.harness = harness or BenchmarkIndexHarness(chunks)
        self.queries = COLLEGE_EVALUATION_QUERIES

    def evaluate_method(
        self,
        method_name: str,
        retrieval_func,
        top_k: int = 10,
    ) -> dict[str, Any]:
        """Evaluate a single retrieval method over all benchmark queries."""
        all_query_metrics: list[dict[str, float]] = []
        latencies_ms: list[float] = []
        per_query_details: list[dict[str, Any]] = []

        for q in self.queries:
            query_text = q["query"]
            gt_chunks = set(q["ground_truth_chunks"])

            start_t = time.perf_counter()
            retrieved = retrieval_func(query_text, top_k=top_k)
            latency = (time.perf_counter() - start_t) * 1000.0
            latencies_ms.append(latency)

            retrieved_chunk_ids = [
                str(r.get("chunk_id") or r.get("id") or "") for r in retrieved
            ]

            q_metrics = calculate_query_metrics(
                retrieved_ids=retrieved_chunk_ids,
                ground_truth_ids=gt_chunks,
                k_values=(1, 3, 5, 10),
            )
            all_query_metrics.append(q_metrics)

            per_query_details.append({
                "query_id": q["query_id"],
                "query": query_text,
                "query_type": q.get("query_type", "unknown"),
                "ground_truth_chunks": list(gt_chunks),
                "retrieved_chunk_ids": retrieved_chunk_ids,
                "top_1_hit": retrieved_chunk_ids[0] in gt_chunks if retrieved_chunk_ids else False,
                "hit_rate@3": q_metrics["hit_rate@3"],
                "mrr": q_metrics["mrr"],
                "latency_ms": round(latency, 2),
            })

        # Compute averages across all queries
        avg_metrics: dict[str, float] = {}
        for key in all_query_metrics[0].keys():
            avg_metrics[key] = sum(m[key] for m in all_query_metrics) / len(all_query_metrics)

        avg_metrics["avg_latency_ms"] = sum(latencies_ms) / len(latencies_ms)

        return {
            "method": method_name,
            "metrics": avg_metrics,
            "per_query_details": per_query_details,
        }

    def run_all_evaluations(self, top_k: int = 5) -> dict[str, Any]:
        """Run complete benchmark across Dense, Sparse, Hybrid (RRF), and Hybrid + Cross-Encoder."""
        print("\n" + "=" * 80)
        print("  STARTING RAG RETRIEVAL BENCHMARK EVALUATION (COLLEGE DATASET)")
        print("=" * 80)

        methods = [
            ("DENSE (Embeddings)", lambda q, top_k: self.harness.retrieve_dense(q, top_k=top_k)),
            ("SPARSE (BM25S)", lambda q, top_k: self.harness.retrieve_sparse(q, top_k=top_k)),
            ("HYBRID (RRF)", lambda q, top_k: self.harness.retrieve_hybrid_rrf(q, top_k=top_k)),
            ("HYBRID + CROSS-ENCODER", lambda q, top_k: self.harness.retrieve_hybrid_cross_encoder(q, top_k=top_k)),
        ]

        results = {}
        for name, func in methods:
            print(f"Evaluating: {name} ...")
            res = self.evaluate_method(name, func, top_k=top_k)
            results[name] = res

        self.print_summary_table(results)
        self.print_query_type_breakdown(results)
        return results

    def print_summary_table(self, results: dict[str, Any]):
        """Print a formatted comparative markdown/ASCII table."""
        header = f"| {'Retrieval Method':<24} | {'Hit@1':<7} | {'Hit@3':<7} | {'Recall@3':<9} | {'Prec@3':<8} | {'MRR':<7} | {'MAP':<7} | {'NDCG@3':<8} | {'Latency':<9} |"
        sep = f"|{'-'*26}|{'-'*9}|{'-'*9}|{'-'*11}|{'-'*10}|{'-'*9}|{'-'*9}|{'-'*10}|{'-'*11}|"

        print("\n" + "=" * 105)
        print("                        OVERALL BENCHMARK COMPARISON TABLE")
        print("=" * 105)
        print(header)
        print(sep)

        for name, data in results.items():
            m = data["metrics"]
            row = (
                f"| {name:<24} "
                f"| {m['hit_rate@1']*100:>5.1f}% "
                f"| {m['hit_rate@3']*100:>5.1f}% "
                f"| {m['recall@3']*100:>7.1f}% "
                f"| {m['precision@3']*100:>6.1f}% "
                f"| {m['mrr']:>7.3f} "
                f"| {m['map']:>7.3f} "
                f"| {m['ndcg@3']:>8.3f} "
                f"| {m['avg_latency_ms']:>6.1f} ms |"
            )
            print(row)
        print(sep)

    def print_query_type_breakdown(self, results: dict[str, Any]):
        """Print performance breakdown segmented by query type (Keyword, Semantic, Hybrid)."""
        query_types = sorted(list(set(q.get("query_type", "other") for q in self.queries)))

        print("\n" + "=" * 90)
        print("                   PERFORMANCE BY QUERY TYPE (MRR / Hit@3)")
        print("=" * 90)

        header = f"| {'Query Category':<18} | " + " | ".join(f"{name:<22}" for name in results.keys()) + " |"
        print(header)
        print("|" + "|".join(["-" * 20] + ["-" * 24] * len(results)) + "|")

        for q_type in query_types:
            row_items = [f"| {q_type.capitalize():<18} |"]
            for name, data in results.items():
                matching_queries = [
                    d for d in data["per_query_details"] if d["query_type"] == q_type
                ]
                if matching_queries:
                    avg_mrr = sum(d["mrr"] for d in matching_queries) / len(matching_queries)
                    avg_hit3 = sum(d["hit_rate@3"] for d in matching_queries) / len(matching_queries)
                    row_items.append(f" MRR: {avg_mrr:.2f} (Hit: {avg_hit3*100:.0f}%) |")
                else:
                    row_items.append(f" {'N/A':<22} |")
            print("".join(row_items))
        print("=" * 90)


if __name__ == "__main__":
    evaluator = RetrievalEvaluator()
    evaluator.run_all_evaluations(top_k=5)
