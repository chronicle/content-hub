from __future__ import annotations
class IntsightsManagerError(Exception):
    """
    General Exception for Intsights manager
    """

    pass


class IntsightsGeneralError(Exception):
    """
    General Exception for Intsights manager
    """

    pass


class AlertNotFoundError(IntsightsManagerError):
    """
    Alert Not Found in Intsight Exception
    """

    pass


class UserNotFoundError(IntsightsManagerError):
    """
    User Not Found in Intsight Exception
    """

    pass


class ChangeAssigneeError(IntsightsManagerError):
    """
    Change Assignee in Intsight Exception
    """

    pass


class BadCredentialsError(IntsightsManagerError):
    """
    Unauthorized access in Intsights Exception
    """

    pass


class IntsightsAlreadyExistsError(IntsightsManagerError):
    pass


class NotFoundError(IntsightsManagerError):
    pass
