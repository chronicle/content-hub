from __future__ import annotations
class HTTPException(Exception):
    """Exception in case of HTTP error."""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code
