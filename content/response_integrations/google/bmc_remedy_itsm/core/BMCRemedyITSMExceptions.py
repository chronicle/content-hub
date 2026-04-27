from __future__ import annotations
class BMCRemedyITSMException(Exception):
    """
    General exception for BMCRemedyITSM
    """

    pass


class BMCRemedyITSMClientErrorException(BMCRemedyITSMException):
    """
    Exception in case of Client Error
    """

    pass


class BMCRemedyITSMNotFoundException(BMCRemedyITSMException):
    """
    Exception for not found case
    """

    pass


class BMCRemedyITSMServerErrorException(BMCRemedyITSMException):
    """
    Exception for server error
    """

    pass


class BMCRemedyITSMTimeoutException(BMCRemedyITSMException):
    """
    Exception for timeout
    """

    pass


class BMCRemedyITSMJobException(BMCRemedyITSMException):
    """
    Exception for job
    """

    pass
