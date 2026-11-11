from __future__ import annotations
class HashiCorpVaultException(Exception):
    """
    General exception for HashiCorpVault
    """


class NotFoundException(HashiCorpVaultException):
    """
    General Object Not found exception.
    """


class InvalidJsonBuilderExpression(HashiCorpVaultException):
    """
    General exception for Invalid Json
    """
