
import os
from celery import Celery
from kombu import Queue
from backend.rag.config.settings import REDIS_URL
REDIS_URL = os.getenv(
    REDIS_URL,
    "redis://localhost:6379/0"
)

celery = Celery(
    "ingestion",
    broker=REDIS_URL,
    backend=os.getenv(
        "CELERY_RESULT_BACKEND",
        "redis://localhost:6379/1"
    ),
    include=["tasks"],
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
