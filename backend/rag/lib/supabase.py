"""Supabase client setup.

Keeping construction here makes the rest of the application easy to test: imports
do not fail when the local environment has not been configured yet.
"""

import os
from functools import lru_cache

from supabase import Client, create_client


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be configured")
    return create_client(url, key)

@lru_cache(maxsize=1)
def get_supabase_admin_client() -> Client:
    """Return the server-only client used for privileged auth workflows.

    Never expose the service-role key to the frontend or use this client from
    ordinary user-request data access.
    """
    url = os.getenv("SUPABASE_URL")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not service_role_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured")
    return create_client(url, service_role_key)
