from __future__ import annotations
class AxoniusManagerError(Exception):
    """
    General Exception for Axonius manager
    """

    pass


class AxoniusManagerMandatoryParametersError(Exception):
    """
    Mandatory Parameters Exception for Axonius manager
    """

    pass


class AxoniusValidationError(Exception):
    """
    Validation Exception for Axonius manager
    """

    pass


class AxoniusAuthorizationError(Exception):
    """
    Authorization Exception for Axonius manager
    """

    pass


class AxoniusForbiddenError(Exception):
    """
    Forbidden Exception for Axonius manager
    """

    pass
