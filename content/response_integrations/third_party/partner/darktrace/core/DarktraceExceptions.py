class DarktraceException(Exception):
    """
    General exception for Darktrace
    """

    pass


class NotFoundException(Exception):
    """
    Exception for not found case
    """

    pass


class ErrorInResponseException(Exception):
    """
    Exception in the case when there is error in response
    """

    pass


class AlreadyAppliedException(Exception):
    """
    Exception for already applied case
    """

    pass


class IncompleteInformationException(Exception):
    """
    Exception in case of incomplete information
    """

    pass


class InvalidTimeException(Exception):
    """
    Exception for invalid time
    """

    pass


class NegativeValueException(Exception):
    """
    Exception for negative value
    """

    pass
