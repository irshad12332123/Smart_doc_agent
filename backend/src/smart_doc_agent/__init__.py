import sys
from pathlib import Path

# Add 'rag' and 'backend' to sys.path
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent.parent)
_RAG_DIR = str(Path(__file__).resolve().parent.parent.parent / "rag")
if _RAG_DIR not in sys.path:
    sys.path.insert(0, _RAG_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


def main() -> None:
    from app import app
    from config.settings import PORT

    app.run(port=PORT, debug=True)
