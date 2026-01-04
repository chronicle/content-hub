from __future__ import annotations


class OrcaSecurityException(Exception):
    """
    General exception for Orca Security
    """

    pass


class OrcaSecurityDuplicatedDataException(Exception):
    """
    Exception in case of duplicated data
    """

    pass


class OrcaSecurityExistingProcessException(Exception):
    """
    Exception in case of existing process
    """

    pass


class OrcaSecurityInvalidParameterException(Exception):
    """
    Exception in case of invalid parameters
    """
