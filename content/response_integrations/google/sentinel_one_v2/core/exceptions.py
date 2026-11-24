from __future__ import annotations
class SentinelOneV2Error(Exception):
    """
    Custom Error.
    """

    pass


class SentinelOneV2ManagerError(SentinelOneV2Error):
    """
    Custom Error.
    """

    pass


class SentinelOneV2UnauthorizedError(SentinelOneV2Error):
    """
    Custom Error.
    """

    pass


class SentinelOneV2HTTPError(SentinelOneV2Error):
    """
    Custom Error.
    """

    pass


class SentinelOneV2ConnectivityError(SentinelOneV2Error):
    """
    Custom Error.
    """

    pass


class SentinelOneV2PermissionError(SentinelOneV2Error):
    """
    Permissions Error.
    """

    pass


class SentinelOneV2NotFoundError(SentinelOneV2Error):
    """
    Not Found Error.
    """

    pass


class SentinelOneV2AlreadyExistsError(SentinelOneV2Error):
    """
    Already Exists Error.
    """

    pass


class SentinelOneV2BadRequestError(SentinelOneV2Error):
    """
    Bad Request Error.
    """

    pass


class SentinelOneV2ValidationError(SentinelOneV2Error):
    """
    Parameter Validation Error.
    """

    pass


class SentinelOneV2TooManyRequestsError(SentinelOneV2ManagerError):
    """
    Too Many Requests Error.
    """

    pass


class SentinelOneV2UnsupportedApiVersionError(SentinelOneV2ManagerError):
    """
    Unsupported api version Error.
    """

    def __init__(self, supported_versions=None, message=None):
        self.message = (
            message
            or "Invalid API version provided. Only {} version are supported.".format(
                " or ".join(f'"{version}"' for version in supported_versions)
            )
        )
        super().__init__(self.message)


class SiteNameNotFoundError(SentinelOneV2Error):
    """Site Name Not Found Error."""