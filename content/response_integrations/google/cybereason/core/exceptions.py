from __future__ import annotations
class CybereasonError(Exception):
    pass


class CybereasonManagerError(CybereasonError):
    pass


class CybereasonManagerNotFoundError(CybereasonError):
    pass


class CybereasonTimeoutError(CybereasonError):
    pass


class CybereasonManagerIsolationError(CybereasonError):
    def __init__(self, message, status="Unknown error"):
        super(CybereasonManagerIsolationError, self).__init__(message)
        self.status = status


class CybereasonNotFoundError(CybereasonError):
    pass


class CybereasonSuccessWithFailureError(CybereasonError):
    pass


class CybereasonClientError(CybereasonError):
    pass


class CybereasonInvalidQueryError(CybereasonError):
    pass


class CybereasonInvalidFormatError(CybereasonError):
    pass


class CybereasonMalopProcessError(CybereasonError):
    """Malop processes/files not found in malop ID API response."""


class CybereasonUniqueIdError(CybereasonError):
    """Action Param "Values" processes/files not found in Malop API response."""


class CybereasonCertificateError(CybereasonError):
    """Raise if Cybereason certificate is not validated."""
