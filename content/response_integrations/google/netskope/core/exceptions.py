from __future__ import annotations


class NetskopeParamError(Exception):
    """
    General Exception for Netskope param error
    """


class NetskopeDataNotFoundError(Exception):
    """General Exception for not able to retrieve data from the API."""


class NetskopeAlreadyProcessedError(Exception):
    """Exception for already processed quarantine incidents."""


class NetskopeManagerV2Error(Exception):
    """Exception for Netskope V2 Manager errors."""


class NetskopeAuthError(Exception):
    """Exception for Netskope authentication errors."""
