from __future__ import annotations
class GoogleAlertCenterException(Exception):
    """
    General exception for GoogleAlertCenter
    """

    pass


class GoogleAlertCenterInvalidJsonException(Exception):
    """
    Exception in case of Invalid JSON
    """

    pass


class AlertNotFoundException(GoogleAlertCenterException):
    pass
