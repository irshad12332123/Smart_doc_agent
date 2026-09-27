import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    ranked_lists: list[list[dict[str, Any]]],
    k: int = 60,
    weights: Optional[list[float]] = None,
) -> list[dict[str, Any]]:
    """
    Reciprocal Rank Fusion (RRF) algorithm.

    Formula:
        RRF_Score(d) = sum_{m in M} ( w_m / (k + rank_m(d)) )

    Parameters:
    -----------
    ranked_lists : list of list of dict
        List containing ranked lists of chunk dictionaries from different retrievers
        (e.g., [dense_results, sparse_results]).
    k : int, default=60
        Smoothing constant. Standard IR value is 60.
    weights : list of float, optional
        Weights for each retriever list. Defaults to equal weighting (1.0 for each).

    Returns:
    --------
    list of dict
        Merged list of chunks sorted in descending order of their fused RRF score.
    """
    if not ranked_lists:
        return []

    # Filter out empty candidate lists
    active_lists = [lst for lst in ranked_lists if lst]
    if not active_lists:
        return []

    if weights is None:
        weights = [1.0] * len(ranked_lists)
    elif len(weights) != len(ranked_lists):
        raise ValueError("Length of weights must match the number of ranked_lists")

    scores: dict[str, float] = {}
    doc_lookup: dict[str, dict[str, Any]] = {}
    rank_history: dict[str, dict[str, int]] = {}

    for list_idx, ranked_list in enumerate(ranked_lists):
        weight = weights[list_idx]
        for rank, doc in enumerate(ranked_list, start=1):
            doc_id = str(doc.get("chunk_id") or doc.get("id") or "")
            if not doc_id:
                continue

            # Calculate RRF score component
            score_delta = weight / (k + rank)
            scores[doc_id] = scores.get(doc_id, 0.0) + score_delta

            if doc_id not in rank_history:
                rank_history[doc_id] = {}
            rank_history[doc_id][f"retriever_{list_idx}_rank"] = rank

            # Store / merge document metadata
            if doc_id not in doc_lookup:
                doc_lookup[doc_id] = dict(doc)
            else:
                # Merge any missing fields if available
                existing = doc_lookup[doc_id]
                for key, val in doc.items():
                    if key not in existing or not existing[key]:
                        existing[key] = val

    # Sort merged documents by accumulated RRF score
    sorted_doc_ids = sorted(scores.keys(), key=lambda did: scores[did], reverse=True)

    fused_results: list[dict[str, Any]] = []
    for rank_pos, doc_id in enumerate(sorted_doc_ids, start=1):
        item = dict(doc_lookup[doc_id])
        item["rrf_score"] = scores[doc_id]
        item["score"] = scores[doc_id]
        item["similarity"] = scores[doc_id]
        item["rrf_rank"] = rank_pos
        item["ranks_in_sources"] = rank_history.get(doc_id, {})
        fused_results.append(item)

    return fused_results


class RRFEngine:
    """Class wrapper for Reciprocal Rank Fusion."""

    def __init__(self, k: int = 60):
        self.k = k

    def fuse(
        self,
        ranked_lists: list[list[dict[str, Any]]],
        weights: Optional[list[float]] = None,
    ) -> list[dict[str, Any]]:
        return reciprocal_rank_fusion(ranked_lists, k=self.k, weights=weights)
