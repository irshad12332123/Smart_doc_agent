"""
Deprecated: result_evaluator is superseded by evidence_evaluator.
Re-exported for backward compatibility.
"""
try:
    from backend.rag.evaluator.evidence_evaluator import EvidenceEvaluator
except ImportError:
    try:
        from rag.evaluator.evidence_evaluator import EvidenceEvaluator
    except ImportError:
        from evaluator.evidence_evaluator import EvidenceEvaluator

__all__ = ["EvidenceEvaluator"]
