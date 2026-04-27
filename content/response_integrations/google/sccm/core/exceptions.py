from __future__ import annotations
from .UtilsManager import encode_sensitive_data


class SCCMWithoutSensitiveDataError(Exception):
    """
    General Exception without sensitive data
    """

    def __init__(self, message, sensitive_data_arr):
        super().__init__(encode_sensitive_data(str(message), sensitive_data_arr))


class SCCMManagerError(SCCMWithoutSensitiveDataError):
    """
    General Exception for SCCM manager
    """

    pass


class QueryException(SCCMWithoutSensitiveDataError):
    """
    Exception for WHL query
    """

    pass
