from __future__ import annotations
class McAfeeEpoException(Exception):
    pass


class McAfeeEpoManagerException(McAfeeEpoException):
    pass


class McAfeeInvalidParamException(McAfeeEpoException):
    pass


class McAfeeEpoCertificateException(McAfeeEpoManagerException):
    pass


class McAfeeEpoInvalidGroupException(McAfeeEpoManagerException):
    pass


class McAfeeEpoUnauthorizedException(McAfeeEpoManagerException):
    pass


class McAfeeEpoPermissionException(McAfeeEpoManagerException):
    pass


class McAfeeEpoBadRequestException(McAfeeEpoManagerException):
    pass


class McAfeeEpoNotFoundException(McAfeeEpoManagerException):
    pass


class McAfeeEpoTaskNotFoundException(McAfeeEpoManagerException):
    pass


class McAfeeEpoMissingEntityException(McAfeeEpoException):
    pass
