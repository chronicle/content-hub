from __future__ import annotations
class ArcsightError(Exception):
    """
    General Arcsight exception
    """

    pass


class ArcsightInvalidParamError(ArcsightError):
    """
    General Exception for arcsight invalid input param's exception
    """

    pass


class ArcsightLoginError(ArcsightError):
    """
    General Exception for arcsight login failure
    """

    pass


class ColumnNotFoundException(ArcsightError):
    pass


class ArcsightApiError(ArcsightError):
    """
    General Exception for arcsight api manager
    """

    pass


class UnableToParseException(ArcsightError):
    """
    Exception if unable to parse value
    """

    def __init__(self, key, value):
        self.key = key
        self.value = value


class ArcsightNoEntitiesFoundError(ArcsightError):
    """
    General Exception for arcsight no entities were found
    """

    pass
