from __future__ import annotations
class TruSTARException(Exception):
    """
    General Exception for TruSTAR manager
    """

    pass


class TruSTARUnauthorizedException(Exception):
    """
    UnAuthorized Exception for TruSTAR manager
    """

    pass


class TruSTARValidationException(Exception):
    """
    Validation Exception for TruSTAR manager
    """

    pass


class TruSTARMissingEnclaveException(Exception):
    """
    Missing enclave Exception for TruSTAR manager
    """

    pass


class TruSTARNoDataException(Exception):
    """
    No Data Exception for TruSTAR manager
    """

    pass
