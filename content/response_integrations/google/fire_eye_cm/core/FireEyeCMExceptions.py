from __future__ import annotations
class FireEyeCMException(Exception):
    pass


class IncorrectHashTypeException(FireEyeCMException):
    pass


class FireEyeCMUnsuccessfulOperationError(FireEyeCMException):
    """
    Unsuccessful operation in FireEye CM
    """

    pass


class FireEyeCMSensorApplianceNotFound(FireEyeCMException):
    """
    Sensor appliance wasn't found Exception in FireEye CM
    """

    pass


class FireEyeCMNotFoundException(FireEyeCMException):
    """
    Not Found Exception in FireEye CM
    """

    pass


class FireEyeCMValidationException(FireEyeCMException):
    """
    Validation Exception for FireEye CM
    """

    pass


class FireEyeCMDownloadFileError(FireEyeCMException):
    """
    Unsuccessful download of a file exception for FireEye CM
    """

    pass
