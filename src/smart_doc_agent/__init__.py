import sys
from pathlib import Path

# Add 'rag' to sys.path
_RAG_DIR = str(Path(__file__).resolve().parent.parent.parent / "rag")
if _RAG_DIR not in sys.path:
    sys.path.insert(0, _RAG_DIR)


def main() -> None:
    from app import app
    from config.settings import PORT

    app.run(port=PORT, debug=True)
