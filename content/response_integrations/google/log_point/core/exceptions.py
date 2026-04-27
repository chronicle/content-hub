from __future__ import annotations
class LogPointApiException(Exception):
    """
    LogPoint API exception
    """

    pass


class LogPointCredentialsException(Exception):
    """
    LogPoint API exception
    """

    pass


class LogPointInvalidParametersException(Exception):
    """
    LogPoint API exception
    """


class LogPointNotFoundException(Exception):
    """
    LogPoint Not Found exception
    """

    pass


class LogPointTimeoutException(Exception):
    """
    LogPoint Timeout exception
    """


class LogPoIntInsufficientEntityTypesException(Exception):
    """
    LogPoint Insufficient entity types exception
    """

    pass


class LogPointUnsuccessfulQueryResultsException(Exception):
    """
    LogPoint Unsuccessful query results exception
    """

    pass
