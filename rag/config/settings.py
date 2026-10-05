import os

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
PORT = int(os.getenv("PORT", "8000"))
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
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
AUTH_ALLOWED_ORIGINS = os.getenv("AUTH_ALLOWED_ORIGINS", "http://localhost:5173")

# BM25 Sparse Retriever settings
BM25_INDEX_DIR = os.getenv(
    "BM25_INDEX_DIR",
    str(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "bm25_index"))
)

BM25_DEFAULT_K = int(os.getenv("BM25_DEFAULT_K", "10"))

# Hybrid, RRF and Re-ranker settings
CROSS_ENCODER_MODEL_NAME = os.getenv(
    "CROSS_ENCODER_MODEL_NAME", "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

RRF_K = int(os.getenv("RRF_K", "60"))
HYBRID_TOP_K = int(os.getenv("HYBRID_TOP_K", "10"))
CROSS_ENCODER_TOP_K = int(os.getenv("CROSS_ENCODER_TOP_K", "5"))
