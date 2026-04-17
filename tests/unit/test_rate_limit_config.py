from src.core.rate_limit import limiter, default_limit
from src.core.config import settings


def test_limiter_has_default_limit_configured():
    assert limiter is not None
    assert default_limit == f"{settings.rate_limit_requests}/{settings.rate_limit_period}seconds"


def test_limiter_enabled_follows_settings():
    assert limiter.enabled == settings.rate_limit_enabled
