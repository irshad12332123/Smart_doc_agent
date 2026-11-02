
import time
import logging
from functools import wraps

logger = logging.getLogger("rag.performance")

def measure_node(node_name, func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        start = time.perf_counter()

        try:
            return func(*args, **kwargs)

        finally:
            elapsed = time.perf_counter() - start

            logger.warning(
                "NODE_PERFORMANCE | node=%s | duration_ms=%.2f",
                node_name,
                elapsed * 1000
            )

    return wrapper
