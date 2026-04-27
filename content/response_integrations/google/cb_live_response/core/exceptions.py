from __future__ import annotations
class CBLiveResponseException(Exception):
    """
    General Exception for CB Live Response manager
    """

    pass


class CBLiveResponseUnauthorizedError(Exception):
    """
    Unauthorized exception for CB Live Response manager
    """

    pass


class CBLiveResponseTimeoutException(Exception):
    """
    Timeout exception for CB Live Response manager
    """

    pass
