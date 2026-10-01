import math
from typing import Sequence, Set, Union


def hit_rate_at_k(
    retrieved_ids: Sequence[str],
    ground_truth_ids: Union[Set[str], Sequence[str]],
    k: int = 5,
) -> float:
    """
    Hit Rate @ K: 1.0 if at least one ground truth ID is present in the top-K retrieved IDs, else 0.0.
    """
    gt_set = set(ground_truth_ids)
    top_k = retrieved_ids[:k]
    return 1.0 if any(doc_id in gt_set for doc_id in top_k) else 0.0


def precision_at_k(
    retrieved_ids: Sequence[str],
    ground_truth_ids: Union[Set[str], Sequence[str]],
    k: int = 5,
) -> float:
    """
    Precision @ K: Proportion of retrieved documents in top-K that are relevant.
    """
    if k <= 0:
        return 0.0
    gt_set = set(ground_truth_ids)
    top_k = retrieved_ids[:k]
    relevant_retrieved = sum(1 for doc_id in top_k if doc_id in gt_set)
    return relevant_retrieved / k


def recall_at_k(
    retrieved_ids: Sequence[str],
    ground_truth_ids: Union[Set[str], Sequence[str]],
    k: int = 5,
) -> float:
    """
    Recall @ K: Proportion of relevant documents successfully retrieved in top-K.
    """
    gt_set = set(ground_truth_ids)
    if not gt_set:
        return 1.0
    top_k = retrieved_ids[:k]
    relevant_retrieved = sum(1 for doc_id in top_k if doc_id in gt_set)
    return relevant_retrieved / len(gt_set)


def reciprocal_rank(
    retrieved_ids: Sequence[str],
    ground_truth_ids: Union[Set[str], Sequence[str]],
) -> float:
    """
    Reciprocal Rank (RR): 1 / rank of the first relevant document in the retrieved list.
    Returns 0.0 if no relevant document is retrieved.
    """
    gt_set = set(ground_truth_ids)
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in gt_set:
            return 1.0 / rank
    return 0.0


def average_precision(
    retrieved_ids: Sequence[str],
    ground_truth_ids: Union[Set[str], Sequence[str]],
    k: int = 10,
) -> float:
    """
    Average Precision (AP @ K): Area under the precision-recall curve for a query.
    """
    gt_set = set(ground_truth_ids)
    if not gt_set:
        return 1.0

    score = 0.0
    num_hits = 0

    top_k = retrieved_ids[:k]
    for rank, doc_id in enumerate(top_k, start=1):
        if doc_id in gt_set:
            num_hits += 1
            score += num_hits / rank

    return score / min(len(gt_set), k) if gt_set else 0.0


def ndcg_at_k(
    retrieved_ids: Sequence[str],
    ground_truth_ids: Union[Set[str], Sequence[str]],
    k: int = 5,
) -> float:
    """
    Normalized Discounted Cumulative Gain (NDCG @ K) with binary relevance.
    """
    gt_set = set(ground_truth_ids)
    if not gt_set or k <= 0:
        return 0.0

    top_k = retrieved_ids[:k]
    dcg = 0.0
    for i, doc_id in enumerate(top_k):
        rel = 1.0 if doc_id in gt_set else 0.0
        dcg += rel / math.log2(i + 2)

    # Ideal DCG
    idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(gt_set), k)))
    return dcg / idcg if idcg > 0 else 0.0


def calculate_query_metrics(
    retrieved_ids: Sequence[str],
    ground_truth_ids: Union[Set[str], Sequence[str]],
    k_values: tuple[int, ...] = (1, 3, 5, 10),
) -> dict[str, float]:
    """
    Calculate all standard IR metrics for a single query.
    """
    metrics = {
        "mrr": reciprocal_rank(retrieved_ids, ground_truth_ids),
        "map": average_precision(retrieved_ids, ground_truth_ids, k=max(k_values)),
    }

    for k in k_values:
        metrics[f"hit_rate@{k}"] = hit_rate_at_k(retrieved_ids, ground_truth_ids, k=k)
        metrics[f"precision@{k}"] = precision_at_k(retrieved_ids, ground_truth_ids, k=k)
        metrics[f"recall@{k}"] = recall_at_k(retrieved_ids, ground_truth_ids, k=k)
        metrics[f"ndcg@{k}"] = ndcg_at_k(retrieved_ids, ground_truth_ids, k=k)

    return metrics
