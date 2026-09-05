from rag.services.retriever.base import BaseRetriever

from typing import Any
from rag.lib.supabase import get_supabase_client
from rag.embedder.embedding import Embedder
from rag.config.settings import RETRIEVAL_MATCH_THRESHOLD, RETRIEVAL_MATCH_COUNT

class DenseRetriever(BaseRetriever):

    def retrieve(self, query: str):

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

        return self._data(result)
