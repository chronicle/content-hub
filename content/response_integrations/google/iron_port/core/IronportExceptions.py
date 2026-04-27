from __future__ import annotations
class IronportManagerException(Exception):
    """
    General Exception for Ironport Manager API
    """

    pass


class IronportIncorrectCredentialsException(IronportManagerException):
    pass


class IronportAsyncOSConnectionException(IronportManagerException):
    pass


class IronportSSHConnectionException(IronportManagerException):
    pass


class IronportAsyncOSMessagesException(IronportManagerException):
    pass


class IronportAsyncOSReportException(IronportManagerException):
    pass
