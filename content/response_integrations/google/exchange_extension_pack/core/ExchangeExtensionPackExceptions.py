from __future__ import annotations
class ExchangeExtensionPackException(Exception):
    """
    General exception for Exchange Extension Pack
    """

    pass


class ExchangeExtensionPackPowershellException(ExchangeExtensionPackException):
    """
    Powershell not installed exception
    """

    pass


class ExchangeExtensionPackGssntlmsspException(ExchangeExtensionPackException):
    """
    Gssntlmssp not installed exception
    """

    pass


class ExchangeExtensionPackIncompleteInfoException(ExchangeExtensionPackException):
    """
    Exception in case incomplete information
    """

    pass


class ExchangeExtensionPackNoResults(ExchangeExtensionPackException):
    """
    Exception in case of no results
    """

    pass


class ExchangeExtensionPackNotFound(ExchangeExtensionPackException):
    """
    Exception for not found case
    """

    pass


class ExchangeExtensionPackAlreadyExist(ExchangeExtensionPackException):
    """
    Exception for already exist case
    """

    pass


class ExchangeExtensionPackSessionError(ExchangeExtensionPackException):
    """
    Exception in case of failed powershell session creation
    """

    pass


class ExchangeExtensionPackInvalidQuery(ExchangeExtensionPackException):
    """
    Exception in case of invalid query
    """

    pass


class ExchangeExtensionPackIncompleteParametersException(
    ExchangeExtensionPackException
):
    """
    Exception in case of incomplete parameters
    """

    pass
