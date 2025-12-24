from __future__ import annotations


class VectraRUXException(Exception):
    """Common VectraRUX Exception"""


class InternalSeverError(VectraRUXException):
    """Internal Server Error"""


class ItemNotFoundException(VectraRUXException):
    """Exception if item not found in VectraRUX"""


class TagsUpdateFailException(VectraRUXException):
    """Exception if failed to updated tags"""


class AddTagException(VectraRUXException):
    """Exception while adding the tags"""


class RateLimitException(VectraRUXException):
    """Exception for rate limit"""


class InvalidIntegerException(VectraRUXException):
    """Invalide integer Exception"""


class BadRequestException(VectraRUXException):
    """Exception for bad request"""


class InvalidDetectionIDException(VectraRUXException):
    """Invalid detection IDs Exception"""


class LongURIException(VectraRUXException):
    """Long URI Exception"""


class UserNotPermittedException(VectraRUXException):
    """Exception while updating assignment"""


class RequestEntityTooLargeException(VectraRUXException):
    """Request Entity Too Large for URL Exception"""


class FileNotFoundException(VectraRUXException):
    """File not found Exception"""


class UnauthorizeException(VectraRUXException):
    """Unauthorized user"""


class RefreshTokenException(VectraRUXException):
    """Exception if refresh token is expired or invalid"""
