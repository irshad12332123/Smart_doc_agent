from sentence_transformers import SentenceTransformer
from config.settings import EMBEDDING_MODEL_NAME
from typing import Sequence


class Embedder:
    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self, model_name: str = EMBEDDING_MODEL_NAME) -> SentenceTransformer:
        if self.model is None:
            self.model = SentenceTransformer(model_name)
            print("----- MODEL LOADED SUCCESSFULLY -----")
        return self.model

    def generate_embeddings(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._load_model()

        embeddings = model.encode(
            list(texts), convert_to_numpy=True, show_progress_bar=False, normalize_embeddings=True
        )
        return embeddings.tolist()


