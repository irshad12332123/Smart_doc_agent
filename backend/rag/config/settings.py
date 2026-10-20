import os

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
PORT = int(os.getenv("PORT", "8000"))
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "google-embedding-2")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "768"))
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "50"))
EMBEDDING_BATCH_DELAY = float(os.getenv("EMBEDDING_BATCH_DELAY", "0.5"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-3.5-flash-lite")
SLM_MODEL_NAME = os.getenv("SLM_MODEL_NAME", "meta-llama/Llama-3.2-1B-Instruct")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
S3_SIGNED_URL_TTL_SECONDS = int(os.getenv("S3_SIGNED_URL_TTL_SECONDS", "300"))
RETRIEVAL_MATCH_COUNT = int(os.getenv("RETRIEVAL_MATCH_COUNT", "5"))
RETRIEVAL_MATCH_THRESHOLD = float(os.getenv("RETRIEVAL_MATCH_THRESHOLD", "0.55"))
HF_TOKEN = os.getenv("HF_TOKEN")
# Authentication settings.  SUPABASE_SERVICE_ROLE_KEY must only ever be present
# on the API server; it is deliberately separate from the browser/anon key.
AUTH_REGISTRATION_TOKEN_SECRET = os.getenv("AUTH_REGISTRATION_TOKEN_SECRET")
AUTH_REGISTRATION_TOKEN_MAX_AGE_SECONDS = int(
    os.getenv("AUTH_REGISTRATION_TOKEN_MAX_AGE_SECONDS", "600")
)
AUTH_ALLOWED_ORIGINS = os.getenv(
    "AUTH_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000,http://localhost:5000,http://127.0.0.1:5000,https://smart-doc-agent-git-main-md-irshads-projects-07456f4e.vercel.app,https://smart-doc-agent-1fcm.onrender.com",
)

# BM25 Sparse Retriever settings
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DEFAULT_BM25_INDEX_DIR = os.path.join(_BACKEND_DIR, "data", "bm25_index")
if not os.path.exists(_DEFAULT_BM25_INDEX_DIR):
    _LEGACY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "bm25_index")
    if os.path.exists(_LEGACY_DIR):
        _DEFAULT_BM25_INDEX_DIR = _LEGACY_DIR

BM25_INDEX_DIR = os.getenv("BM25_INDEX_DIR", _DEFAULT_BM25_INDEX_DIR)

BM25_DEFAULT_K = int(os.getenv("BM25_DEFAULT_K", "10"))

# Hybrid, RRF and Re-ranker settings
CROSS_ENCODER_MODEL_NAME = os.getenv(
    "CROSS_ENCODER_MODEL_NAME", "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

RRF_K = int(os.getenv("RRF_K", "60"))
HYBRID_TOP_K = int(os.getenv("HYBRID_TOP_K", "10"))
CROSS_ENCODER_TOP_K = int(os.getenv("CROSS_ENCODER_TOP_K", "5"))

REDIS_URL = os.getenv(
    "REDIS_URL"
)
