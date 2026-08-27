from dotenv import load_dotenv
from flask import Flask, jsonify, request

# Settings are read while importing the modules below, so load .env first.
load_dotenv()

from config.settings import (
    AUTH_ALLOWED_ORIGINS,
    EMBEDDING_MODEL_NAME,
    GEMINI_MODEL_NAME,
    MAX_UPLOAD_BYTES,
    PORT,
)

from ingestion.ingestion import ingest
from modules.auth.routes import auth
from modules.user.routes import user

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
        return jsonify({
            # Field names are retained so the existing frontend contract stays stable.
            "ollama_ready": bool(__import__("os").getenv("GEMINI_API_KEY")),
            "ollama_message": "Gemini API key configured" if __import__("os").getenv("GEMINI_API_KEY") else "GEMINI_API_KEY is not configured",
            "indexed_chunks": 0,
            "embed_model": EMBEDDING_MODEL_NAME,
            "chat_model": GEMINI_MODEL_NAME,
        })

    return app


app = create_app()


if __name__ == "__main__":
    app.run(port=PORT, debug=True)
