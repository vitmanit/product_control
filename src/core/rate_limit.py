from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.config import settings


default_limit = f"{settings.rate_limit_requests}/{settings.rate_limit_period}seconds"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[default_limit],
    storage_uri=settings.rate_limit_storage_uri,
    enabled=settings.rate_limit_enabled,
)
