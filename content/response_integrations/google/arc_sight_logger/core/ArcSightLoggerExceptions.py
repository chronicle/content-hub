from __future__ import annotations
class ArcSightLoggerException(Exception):
    """
    Common ArcSight Logger Exception
    """

    pass


class QueryExecutionException(ArcSightLoggerException):
    """
    Exception if unable to execute query in ArcSight Logger
    """

    pass
