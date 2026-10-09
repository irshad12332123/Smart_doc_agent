import logging
from typing import Any, Optional

from config.settings import CROSS_ENCODER_MODEL_NAME, CROSS_ENCODER_TOP_K

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """
    Cross-Encoder Re-ranker using SentenceTransformers CrossEncoder.

    Feeds (query, document) pairs into full cross-attention layers
    to calculate precise semantic interaction and relevance scores.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        max_length: int = 512,
        device: Optional[str] = None,
    ):
        self.model_name = model_name or CROSS_ENCODER_MODEL_NAME
        self.max_length = max_length
        self.device = device
        self._model: Optional[Any] = None

    def _load_model(self) -> Any:
        if self._model is None:
            logger.info(f"Loading Cross-Encoder model: {self.model_name}")
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as e:
                raise RuntimeError(
                    "sentence-transformers is required for local Cross-Encoder reranking. "
                    "Install sentence-transformers or disable cross-encoder re-ranking."
                ) from e

            self._model = CrossEncoder(
                self.model_name,
                max_length=self.max_length,
                device=self.device,
            )
        return self._model

    def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_k: Optional[int] = None,
        batch_size: int = 32,
    ) -> list[dict[str, Any]]:
        """
        Re-rank candidate documents based on Cross-Encoder scoring.

        Parameters:
        -----------
        query : str
            The user search query.
        documents : list of dict
            List of candidate chunk dictionaries to re-rank.
        top_k : int, optional
            Maximum number of top re-ranked documents to return.
        batch_size : int, default=32
            Batch size for model inference.

        Returns:
        --------
        list of dict
            Re-ordered list of chunk dictionaries with cross_encoder_score attached.
        """
        if not documents or not query or not query.strip():
            return []

        model = self._load_model()

        # Build (query, text) pairs
        pairs: list[tuple[str, str]] = []
        for doc in documents:
            text = str(doc.get("content") or doc.get("text") or "")
            pairs.append((query.strip(), text))

        try:
            scores = model.predict(
                pairs,
                batch_size=batch_size,
                show_progress_bar=False,
            )
        except Exception as e:
            logger.error(f"Cross-Encoder inference error: {e}. Falling back to original ranking.")
            return documents[:top_k] if top_k else documents

        # Attach scores to documents
        scored_docs: list[dict[str, Any]] = []
        for doc, score_val in zip(documents, scores):
            doc_copy = dict(doc)
            ce_score = float(score_val)
            doc_copy["cross_encoder_score"] = ce_score
            doc_copy["score"] = ce_score
            doc_copy["similarity"] = ce_score
            scored_docs.append(doc_copy)

        # Sort descending by Cross-Encoder score
        scored_docs.sort(key=lambda d: d["cross_encoder_score"], reverse=True)

        limit = top_k or CROSS_ENCODER_TOP_K or len(scored_docs)
        return scored_docs[:limit]
