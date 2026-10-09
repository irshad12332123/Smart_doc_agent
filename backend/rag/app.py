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

import re
from dotenv import load_dotenv
from flask import Flask, jsonify, request, Response

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
    _LOCAL_ORIGIN_REGEX = re.compile(
        r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?$", re.IGNORECASE
    )
    _VERCEL_APP_REGEX = re.compile(
        r"^https://smart-doc-agent.*\.vercel\.app$", re.IGNORECASE
    )
    _STATIC_ALLOWED_ORIGINS = {
        "https://smart-doc-agent-git-main-md-irshads-projects-07456f4e.vercel.app",
        "https://smart-doc-agent-1fcm.onrender.com",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    }

    def _is_origin_allowed(origin: str | None) -> bool:
        if not origin:
            return False
        clean = origin.strip().rstrip("/")
        configured = {
            o.strip().rstrip("/")
            for o in (AUTH_ALLOWED_ORIGINS or "").split(",")
            if o.strip()
        }
        if "*" in configured:
            return True
        if clean in configured or clean in _STATIC_ALLOWED_ORIGINS:
            return True
        if _LOCAL_ORIGIN_REGEX.match(clean):
            return True
        if _VERCEL_APP_REGEX.match(clean):
            return True
        return False

    def _apply_cors_headers(response, origin: str | None):
        if origin and _is_origin_allowed(origin):
            clean_origin = origin.strip().rstrip("/")
            response.headers["Access-Control-Allow-Origin"] = clean_origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"

        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Authorization, X-Requested-With, Accept, Origin"
        )
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD"
        )
        response.headers["Access-Control-Max-Age"] = "86400"
        return response

    @app.before_request
    def handle_options_preflight():
        if request.method == "OPTIONS":
            response = Response("", status=204)
            return _apply_cors_headers(response, request.headers.get("Origin"))

    @app.after_request
    def add_cors_headers(response):
        return _apply_cors_headers(response, request.headers.get("Origin"))

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
