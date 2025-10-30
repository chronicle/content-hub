# Managers/TorqErrors.py

class TorqError(Exception):
    """Base class for Torq integration errors."""

class TorqAuthError(TorqError):
    """401/403: Secret wrong, webhook disabled, or not authorized."""

class TorqRateLimitError(TorqError):
    """429: Rate limit; often transient. Try again with backoff or later."""

class TorqServerError(TorqError):
    """5xx: Torq or upstream is unhealthy. Usually transient; retried."""

class TorqClientError(TorqError):
    """Other 4xx: Bad request/payload/URL. Fix payload or instance config."""

class TorqBadResponseError(TorqError):
    """Response claimed JSON but couldn't be parsed. Check proxies/gateways."""