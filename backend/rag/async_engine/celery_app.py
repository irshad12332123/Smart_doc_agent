import os
import sys
from pathlib import Path
from celery import Celery
from dotenv import load_dotenv
from kombu import Queue

# Ensure backend, rag, and repo root are in sys.path
_CURRENT_DIR = Path(__file__).resolve().parent
_RAG_DIR = _CURRENT_DIR.parent
_BACKEND_DIR = _RAG_DIR.parent
_REPO_DIR = _BACKEND_DIR.parent

for _p in (str(_CURRENT_DIR), str(_RAG_DIR), str(_BACKEND_DIR), str(_REPO_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Load environment variables for standalone Celery workers
load_dotenv(dotenv_path=_BACKEND_DIR / ".env")
load_dotenv(dotenv_path=_RAG_DIR / ".env")
load_dotenv()

try:
    from config.settings import REDIS_URL as SETTINGS_REDIS_URL
except ImportError:
    try:
        from backend.rag.config.settings import REDIS_URL as SETTINGS_REDIS_URL
    except ImportError:
        SETTINGS_REDIS_URL = "redis://localhost:6379/0"

REDIS_URL = os.getenv("REDIS_URL", SETTINGS_REDIS_URL or "redis://localhost:6379/0")


celery = Celery(
    "ingestion",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["async_engine.tasks", "tasks"],
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,

    # Acknowledge a task after execution, not before.
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Avoid fetching too many jobs in advance.
    worker_prefetch_multiplier=1,

    # Route failed jobs to a separate queue.
    task_queues=(
        Queue("ingestion"),
        Queue("dlq"),
    ),
    task_default_queue="ingestion",
)
