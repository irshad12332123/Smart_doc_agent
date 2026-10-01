from typing import Sequence
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer
from config.settings import EMBEDDING_MODEL_NAME

class Embedder(Embeddings):
    def __init__(self):
        self.model = None
        self._load_model()
    def _load_model(self, model_name: str = EMBEDDING_MODEL_NAME) -> SentenceTransformer:
        if self.model is None:
            self.model = SentenceTransformer(model_name)
        return self.model

    def generate_embeddings(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._load_model()

        embeddings = model.encode(
            list(texts), convert_to_numpy=True, show_progress_bar=False, normalize_embeddings=True
        )

        return embeddings.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.generate_embeddings(texts)

    def embed_query(self, text: str) -> list[float]:
        res = self.generate_embeddings([text])
        return res[0] if res else []

