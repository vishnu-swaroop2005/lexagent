from functools import lru_cache
from supabase import create_client, Client

from app.config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    """Get a Supabase client using the service role key.

    Uses service role key for server-side operations, bypassing RLS.
    All queries must still include org_id filtering for multi-tenant isolation.
    """
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_supabase_anon_client() -> Client:
    """Get a Supabase client using the anon key (for RLS-enforced operations)."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_anon_key)
