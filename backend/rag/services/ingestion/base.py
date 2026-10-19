from abc import ABC, abstractmethod
from typing import Any, Optional

try:
    from lib.supabase import get_supabase_admin_client
except ImportError:
    from backend.rag.lib.supabase import get_supabase_admin_client


class BaseIngestion(ABC):
    """Base class for ingestion services.

    Initializes the privileged Supabase admin client (using the service role key)
    on object creation.
    """

    def __init__(self, client: Optional[Any] = None):
        self.client = client if client is not None else get_supabase_admin_client()

    @abstractmethod
    def ingest(self, *args, **kwargs):
        raise NotImplementedError("Subclasses must implement ingest method")
