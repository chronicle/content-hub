from __future__ import annotations
class ZerofoxManagerError(Exception):
    """General Exception for Zerofox manager."""


class AuthenticationError(Exception):
    """Exception in case of authentication failure."""


class AlertNotFoundError(Exception):
    """Exception in case of alert not found."""


class RequestTakeDownError(Exception):
    """Exception in case of request takedown failure."""


class UnsupportedAttachmentError(Exception):
    """Exception in case of unsupported attachment"""
