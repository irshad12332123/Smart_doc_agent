import logging
import os
import re
import time
from typing import Any, Callable, Sequence
from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from config.settings import (
    EMBEDDING_MODEL_NAME,
    EMBEDDING_DIMENSIONS,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_BATCH_DELAY,
    GEMINI_API_KEY,
)

logger = logging.getLogger(__name__)

def _normalize_model_name(model_name: str | None) -> str:
    name = (model_name or "").strip()
    if name in {"google-embedding-2", "models/google-embedding-2", "gemini-embedding-2"}:
        return "models/gemini-embedding-2"
    if name and not name.startswith("models/") and ("embedding" in name or "gemini" in name):
        return f"models/{name}"
    return name or "models/gemini-embedding-2"


class Embedder(Embeddings):
    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL_NAME,
        dimensions: int = EMBEDDING_DIMENSIONS,
        batch_size: int = EMBEDDING_BATCH_SIZE,
        batch_delay: float = EMBEDDING_BATCH_DELAY,
        api_key: str | None = None,
        max_retries: int = 5,
    ):
        self.model_name = _normalize_model_name(model_name)
        self.dimensions = dimensions
        self.batch_size = max(1, batch_size)
        self.batch_delay = max(0.0, batch_delay)
        self.max_retries = max(1, max_retries)
        self.api_key = api_key or GEMINI_API_KEY or os.getenv("GOOGLE_API_KEY")
        self.model: GoogleGenerativeAIEmbeddings | None = None
        self._cache: dict[str, list[float]] = {}
        self._load_model()

    def _load_model(self, model_name: str | None = None) -> GoogleGenerativeAIEmbeddings:
        if self.model is None or (model_name is not None and _normalize_model_name(model_name) != self.model_name):
            if model_name is not None:
                self.model_name = _normalize_model_name(model_name)
            if not self.api_key:
                raise RuntimeError("GEMINI_API_KEY must be configured before using embeddings")
            self.model = GoogleGenerativeAIEmbeddings(
                model=self.model_name,
                google_api_key=self.api_key,
                output_dimensionality=self.dimensions,
            )
        return self.model

    def _execute_with_retry(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute embedding API call with exponential backoff on 429 rate limit errors."""
        attempt = 0
        while True:
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                err_str = str(e)
                is_rate_limit = (
                    "429" in err_str
                    or "RESOURCE_EXHAUSTED" in err_str
                    or "Quota" in err_str
                    or "quota" in err_str
                    or "rate limit" in err_str.lower()
                )

                if is_rate_limit and attempt < self.max_retries:
                    attempt += 1
                    # Extract suggested retry delay from API error message if provided
                    retry_seconds: float = 0.0
                    m1 = re.search(r"retry in ([0-9.]+)s", err_str, re.IGNORECASE)
                    m2 = re.search(r"['\"]retryDelay['\"]:\s*['\"]([0-9.]+)s['\"]", err_str, re.IGNORECASE)

                    if m1:
                        retry_seconds = float(m1.group(1)) + 1.0
                    elif m2:
                        retry_seconds = float(m2.group(1)) + 1.0
                    else:
                        # Exponential backoff: 2s, 4s, 8s, 16s, 32s (capped at 60s)
                        retry_seconds = min(60.0, 2.0 * (2 ** (attempt - 1)))

                    logger.warning(
                        f"Gemini embedding rate limit encountered (attempt {attempt}/{self.max_retries}). "
                        f"Backing off for {retry_seconds:.1f}s before retry..."
                    )
                    time.sleep(retry_seconds)
                else:
                    raise

    def generate_embeddings(
        self, texts: Sequence[str], batch_size: int | None = None
    ) -> list[list[float]]:
        if not texts:
            return []
        model = self._load_model()
        effective_batch_size = batch_size or self.batch_size

        # Identify unique non-empty texts needing API requests
        zero_vector = [0.0] * self.dimensions
        uncached_texts: list[str] = []
        clean_indices: dict[int, str] = {}

        for idx, text in enumerate(texts):
            str_text = str(text) if text is not None else ""
            if not str_text.strip():
                continue
            clean_indices[idx] = str_text
            if str_text not in self._cache and str_text not in uncached_texts:
                uncached_texts.append(str_text)

        # Process uncached texts in batches
        if uncached_texts:
            for i in range(0, len(uncached_texts), effective_batch_size):
                batch = uncached_texts[i : i + effective_batch_size]
                batch_embeddings = self._execute_with_retry(model.embed_documents, batch)

                for t, emb in zip(batch, batch_embeddings, strict=True):
                    self._cache[t] = emb

                # Polite delay between consecutive batches to prevent rate limit spikes
                if i + effective_batch_size < len(uncached_texts) and self.batch_delay > 0:
                    time.sleep(self.batch_delay)

        # Assemble full output list preserving original indices
        embeddings: list[list[float]] = []
        for idx in range(len(texts)):
            if idx in clean_indices:
                t = clean_indices[idx]
                embeddings.append(self._cache.get(t, zero_vector))
            else:
                embeddings.append(list(zero_vector))

        return embeddings

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.generate_embeddings(texts)

    def embed_query(self, text: str) -> list[float]:
        if not text or not str(text).strip():
            return [0.0] * self.dimensions
        str_text = str(text)
        if str_text in self._cache:
            return self._cache[str_text]

        model = self._load_model()
        emb = self._execute_with_retry(model.embed_query, str_text)
        self._cache[str_text] = emb
        return emb
