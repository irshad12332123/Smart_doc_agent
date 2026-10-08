"""Query engine module for query rewriting and deterministic document routing."""

from .router import DocumentRouter, RouterResult
from .rewrite_query import rewrite_query

__all__ = ["DocumentRouter", "RouterResult", "rewrite_query"]
