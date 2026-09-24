from services.retriever.base import BaseRetriever
import bm25s
import Stemmer
from lib.supabase import get_supabase_client

class SparseDocumentSystem(BaseRetriever):

    def retrieve(self, query:str):

        rtreiver = bm25s.BM25()

        supabase_client = get_supabase_client()
        stemmer = Stemmer.Stemmer("english")

        # Fetch the docs from the database



