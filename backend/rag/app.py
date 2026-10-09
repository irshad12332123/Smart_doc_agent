import os
import sys
import time
from pathlib import Path

_START_TIME = time.time()


def _get_rss_mb() -> float:
    """Return current process resident set size (RSS) in megabytes."""
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return float(line.split()[1]) / 1024.0
    except Exception:
        pass
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    except Exception:
        return 0.0


def _log_import_stage(message: str) -> None:
    elapsed = time.time() - _START_TIME
    rss = _get_rss_mb()
    print(f"[Startup {elapsed:5.2f}s | RSS: {rss:5.1f} MB] {message}", flush=True)


# Prevent langchain_core from importing heavy optional packages (transformers/torch)
# which consume 500-800MB of RAM and trigger OOM on 512MB hosting environments like Render.
if os.getenv("DISABLE_LOCAL_TORCH", "1").lower() in ("1", "true", "yes"):
    sys.modules.setdefault("transformers", None)

_log_import_stage("Configuring system paths and environment...")

# Ensure rag directory, backend root, and project root are on sys.path
_RAG_DIR = str(Path(__file__).resolve().parent)
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent)
_REPO_DIR = str(Path(__file__).resolve().parent.parent.parent)

for _p in (_RAG_DIR, _BACKEND_DIR, _REPO_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from dotenv import load_dotenv
from flask import Flask, jsonify, request

# Settings are read while importing the modules below, so load .env first.
load_dotenv(dotenv_path=Path(_BACKEND_DIR) / ".env")
load_dotenv()

_log_import_stage("Loading application settings...")
from config.settings import (
    AUTH_ALLOWED_ORIGINS,
    EMBEDDING_MODEL_NAME,
    GEMINI_MODEL_NAME,
    MAX_UPLOAD_BYTES,
    PORT,
)

_log_import_stage("Importing auth routes...")
from modules.auth.routes import auth

_log_import_stage("Importing user routes...")
from modules.user.routes import user

_log_import_stage("Importing ingestion and retrieval routes...")
from ingestion.ingestion import ingest

_log_import_stage("All modules imported. Initializing Flask app...")


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
    app.register_blueprint(ingest)
    app.register_blueprint(auth)
    app.register_blueprint(user)
    @app.after_request
    def add_cors_headers(response):
        allowed_origins = {
            origin.strip()
            for origin in AUTH_ALLOWED_ORIGINS.split(",")
            if origin.strip()
        }

        origin = request.headers.get("Origin")

        # print("REQUEST ORIGIN:", repr(origin))
        # print("ALLOWED ORIGINS:", allowed_origins)

        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"

        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"

        return response

    @app.get("/api/health")
    def health():
        from pathlib import Path
        import json
        from config.settings import BM25_INDEX_DIR

        meta_file = Path(BM25_INDEX_DIR) / "metadata.json"
        indexed_chunks = 0
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    indexed_chunks = json.load(f).get("total_chunks", 0)
            except Exception:
                indexed_chunks = 0

        return jsonify({
            # Field names are retained so the existing frontend contract stays stable.
            "ollama_ready": bool(__import__("os").getenv("GEMINI_API_KEY")),
            "ollama_message": "Gemini API key configured" if __import__("os").getenv("GEMINI_API_KEY") else "GEMINI_API_KEY is not configured",
            "indexed_chunks": indexed_chunks,
            "embed_model": EMBEDDING_MODEL_NAME,
            "chat_model": GEMINI_MODEL_NAME,
        })

    return app


app = create_app()
_log_import_stage("Flask application created and ready to serve!")


if __name__ == "__main__":
    app.run(port=PORT, debug=True)
