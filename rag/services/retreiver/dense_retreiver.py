from rag.services.retreiver.base_retreiver import BaseRetreiver
from typing import Any
from rag.lib.supabase import get_supabase_client
from rag.embedder.embedding import Embedder
from rag.config.settings import RETRIEVAL_MATCH_THRESHOLD, RETRIEVAL_MATCH_COUNT

def _data(response: Any) -> list[dict[str, Any]]:
    result = getattr(response, "data", response)
    return result if isinstance(result, list) else ([] if result is None else [result])

class DenseRetreiver(BaseRetreiver):
    def retrieve(self, query: str) -> list[dict[str, Any]]:

        embedding = Embedder().generate_embeddings([query])[0]
        client = get_supabase_client()

        result = client.rpc(
            "match_documents",
            {
                "query_embedding": embedding,
                "match_threshold": 0.3 or RETRIEVAL_MATCH_THRESHOLD,
                "match_count": 50 or RETRIEVAL_MATCH_COUNT,
            },
        ).execute()

        return _data(result)
