from __future__ import annotations
class MISPManagerError(Exception):
    """
    General Exception for MISP manager
    """

    pass


class MISPManagerObjectNotFoundError(Exception):
    """
    Object Not Found Exception for MISP manager
    """

    pass


class MISPManagerAttributeNotFoundError(Exception):
    """
    Attribute Not Found Exception for MISP manager
    """

    pass


class MISPManagerTagNotFoundError(Exception):
    """
    Tag Not Found Exception for MISP manager
    """

    pass


class MISPManagerEventIdNotFoundError(Exception):
    """
    Tag Not Found Exception for MISP not found event id
    """

    pass


class MISPManagerInvalidCategoryError(Exception):
    """
    Invalid Provided Category Exception for MISP
    """

    pass


class MISPManagerEventIdNotProvidedError(Exception):
    """
    Not Provided event id Exception for MISP
    """

    pass


class MISPManagerObjectUuidProvidedError(Exception):
    """
    Not Provided event id Exception for MISP
    """

    pass


class MISPManagerCreateEventError(Exception):
    """
    MISP Exception for create event
    """

    pass


class MISPMissingParamError(Exception):
    """
    MISP Exception for missing parameter
    """

    pass


class MISPNotAcceptableParamError(Exception):
    """
    MISP Exception for not acceptable param
    """

    def __init__(self, param_name, opt_msg=""):
        self._message = "Invalid value was provided for the parameter '{}'. {}"
        super().__init__(self._message.format(param_name, opt_msg))


class MISPNotAcceptableNumberOrStringError(MISPNotAcceptableParamError):
    """
    MISP Exception for not acceptable number or string param
    """

    def __init__(self, param_name, *, acceptable_numbers, acceptable_strings):
        opt_msg = f"Acceptable numbers: {','.join(map(str, acceptable_numbers))}. Acceptable strings: {','.join(map(str.capitalize, acceptable_strings))}"

        super().__init__(param_name, opt_msg)


class MISPInvalidFileError(Exception):
    """
    MISP Exception for not found file
    """

    pass


class AttachmentExistsException(Exception):
    """
    MISP Exception for existing attachment
    """

    pass


class MISPCertificateError(Exception):
    """
    MISP Exception for certificate
    """

    pass
