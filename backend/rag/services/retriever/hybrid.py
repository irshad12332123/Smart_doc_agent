import logging
from typing import Any, Optional

from config.settings import (
    CROSS_ENCODER_TOP_K,
    HYBRID_TOP_K,
    RETRIEVAL_MATCH_COUNT,
    RRF_K,
)
from services.fusion.rrf import RRFEngine, reciprocal_rank_fusion
from services.retriever.base import BaseRetriever
from services.retriever.dense import DenseRetriever
from services.retriever.sparse import SparseRetriever

logger = logging.getLogger(__name__)


class HybridRetriever(BaseRetriever):
    """
    Hybrid Document Retriever combining Dense Vector Search and BM25 Sparse Search
    via Reciprocal Rank Fusion (RRF) and optional deep Cross-Encoder re-ranking.
    """

    def __init__(
        self,
        dense_retriever: Optional[DenseRetriever] = None,
        sparse_retriever: Optional[SparseRetriever] = None,
        reranker: Optional[Any] = None,
        rrf_k: int = RRF_K,
    ):
        self.dense_retriever = dense_retriever or DenseRetriever()
        self.sparse_retriever = sparse_retriever or SparseRetriever()
        self.reranker = reranker
        self.rrf_k = rrf_k
        self.rrf_engine = RRFEngine(k=rrf_k)

    def retrieve(
        self,
        query: str,
        match_count: Optional[int] = None,
        dense_k: Optional[int] = None,
        sparse_k: Optional[int] = None,
        dense_weight: float = 1.0,
        sparse_weight: float = 1.0,
        rerank: bool = False,
        rerank_top_k: Optional[int] = None,
        document_ids: Optional[list[str]] = None,
        match_threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        Execute Hybrid Retrieval with RRF and optional Cross-Encoder Re-ranking.

        Parameters:
        -----------
        query : str
            Search query string.
        match_count : int, optional
            Number of final documents to return. Defaults to HYBRID_TOP_K.
        dense_k : int, optional
            Number of candidate chunks to fetch from dense retriever.
        sparse_k : int, optional
            Number of candidate chunks to fetch from sparse retriever.
        dense_weight : float, default=1.0
            Weight of dense retriever in RRF scoring.
        sparse_weight : float, default=1.0
            Weight of sparse retriever in RRF scoring.
        rerank : bool, default=False
            Whether to apply Cross-Encoder re-ranking on fused candidates.
        rerank_top_k : int, optional
            Number of top candidates to re-rank with Cross-Encoder.
        document_ids : list of str, optional
            Filter search to specific document IDs.
        match_threshold : float, default=0.0
            Minimum similarity threshold.

        Returns:
        --------
        list of dict
            Ranked list of chunk dictionaries.
        """
        if not query or not isinstance(query, str) or not query.strip():
            return []

        final_k = match_count or HYBRID_TOP_K or RETRIEVAL_MATCH_COUNT
        candidate_dense_k = dense_k or (final_k * 2)
        candidate_sparse_k = sparse_k or (final_k * 2)

        # 1. Retrieve Dense Candidates
        dense_results: list[dict[str, Any]] = []
        try:
            raw_dense = self.dense_retriever.retrieve(query)
            # Filter if document_ids provided
            if document_ids:
                doc_set = set(document_ids)
                raw_dense = [
                    d for d in raw_dense
                    if str(d.get("document_id") or d.get("doc_id") or "") in doc_set
                ]
            dense_results = raw_dense[:candidate_dense_k]

        except Exception as e:
            logger.error(f"Error during Dense candidate retrieval: {e}")
            dense_results = []

        # 2. Retrieve Sparse Candidates (BM25S)
        sparse_results: list[dict[str, Any]] = []
        try:
            sparse_results = self.sparse_retriever.retrieve(
                query=query,
                match_count=candidate_sparse_k,
                match_threshold=match_threshold,
                document_ids=document_ids,
            )
        except Exception as e:
            logger.error(f"Error during Sparse candidate retrieval: {e}")
            sparse_results = []

        # 3. Reciprocal Rank Fusion (RRF)
        fused_candidates = self.rrf_engine.fuse(
            [dense_results, sparse_results],
            weights=[dense_weight, sparse_weight],
        )

        if not fused_candidates:
            return []

        # 4. Optional Cross-Encoder Re-ranking
        if rerank:
            if self.reranker is None:
                from services.reranker.cross_encoder import CrossEncoderReranker
                self.reranker = CrossEncoderReranker()
            ce_k = rerank_top_k or final_k
            candidates_to_rerank = fused_candidates[:ce_k * 2]
            ranked_results = self.reranker.rerank(
                query=query,
                documents=candidates_to_rerank,
                top_k=final_k,
            )
            return ranked_results

        return fused_candidates[:final_k]
