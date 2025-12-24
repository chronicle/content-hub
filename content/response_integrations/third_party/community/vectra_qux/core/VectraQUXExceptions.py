from __future__ import annotations


class VectraQUXException(Exception):
    """Common VectraQUX Exception"""


class ItemNotFoundException(VectraQUXException):
    """Exception if item not found in VectraQUX"""


class TagsUpdateFailException(VectraQUXException):
    """Exception if failed to updated tags"""


class AddTagException(VectraQUXException):
    """Exception while adding the tags"""


class RateLimitException(VectraQUXException):
    """Exception for rate limit"""


class BadRequestException(VectraQUXException):
    """Exception for bad request"""


class InvalidIntegerException(VectraQUXException):
    """Invalid integer Exception"""


class UserNotPermittedException(VectraQUXException):
    """Exception while updating assignment"""


class LongURIException(VectraQUXException):
    """Long URI Exception"""


class InvalidDetectionIDException(VectraQUXException):
    """Invalid detection IDs Exception"""


class RequestEntityTooLargeException(VectraQUXException):
    """Request Entity Too Large for URL Exception"""


class InternalSeverError(VectraQUXException):
    """Internal Server Error"""


class FileNotFoundException(VectraQUXException):
    """File not found Exception"""
