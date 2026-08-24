import os

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
PORT = int(os.getenv("PORT", "8000"))
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
SLM_MODEL_NAME = os.getenv("SLM_MODEL_NAME", "meta-llama/Llama-3.2-1B-Instruct")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
S3_SIGNED_URL_TTL_SECONDS = int(os.getenv("S3_SIGNED_URL_TTL_SECONDS", "300"))
RETRIEVAL_MATCH_COUNT = int(os.getenv("RETRIEVAL_MATCH_COUNT", "5"))
RETRIEVAL_MATCH_THRESHOLD = float(os.getenv("RETRIEVAL_MATCH_THRESHOLD", "0.5"))

# Authentication settings.  SUPABASE_SERVICE_ROLE_KEY must only ever be present
# on the API server; it is deliberately separate from the browser/anon key.
AUTH_REGISTRATION_TOKEN_SECRET = os.getenv("AUTH_REGISTRATION_TOKEN_SECRET")
AUTH_REGISTRATION_TOKEN_MAX_AGE_SECONDS = int(
    os.getenv("AUTH_REGISTRATION_TOKEN_MAX_AGE_SECONDS", "600")
)
AUTH_ALLOWED_ORIGINS = os.getenv("AUTH_ALLOWED_ORIGINS", "http://localhost:5173")

