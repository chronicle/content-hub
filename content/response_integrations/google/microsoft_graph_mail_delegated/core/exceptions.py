from __future__ import annotations
class MicrosoftGraphMailManagerError(Exception):
    """
    General Exception for microsoft graph mail manager
    """


class InvalidParameterException(Exception):
    """
    Exception in case of invalid parameter
    """


class InvalidAttachmentPathException(Exception):
    """
    Exception in case of invalid attachment path
    """


class TimeoutReachedException(Exception):
    """
    Exception if timeout approached.
    """


class MailboxNotFoundException(Exception):
    """
    Exception if mailbox not found.
    """


class FolderNotFoundException(Exception):
    """
    Exception if mailbox folder not found.
    """


class EmailNotFoundException(Exception):
    """Exception if Email details not found in Microsoft Graph."""


class EmailWithoutAttachmentException(Exception):
    """Exception if Email does not have attachment in Microsoft Graph."""


class SaveFileToGCPError(Exception):
    """Exception if file is unable to save to the Google SecOps GCP bucket."""


class InvalidAttachment(Exception):
    """Exception in case of invalid attachment"""


class UnableToGetValidEmailFromEntity(Exception):
    """Exception if the entity is not a valid email"""


class UserEntityNotFound(Exception):
    """Exception if no USER entity is found"""


class RefreshTokenRetrievalError(Exception):
    """Exception raised when failing to retrieve a refresh token."""


class UnsupportedEntityTypeException(Exception):
    """Exception if entity type is not supported."""


class InvalidRefreshTokenError(Exception):
    """Exception if Refresh Token is invalid."""


class InvalidClientIdError(Exception):
    """Exception if Client ID is invalid."""


class InvalidTenantIdError(Exception):
    """Exception if Tenant ID is invalid."""


class InvalidClientSecretError(Exception):
    """Exception if Client Secret is invalid."""


class InvalidDelegationPermissionError(Exception):
    """Exception if Delegation permission is unavailable."""
