from __future__ import annotations
class AnomaliStaxxException(Exception):
    pass


class AnomaliStaxxConnectivityException(AnomaliStaxxException):
    pass


class AnomaliStaxxAuthorizationException(AnomaliStaxxException):
    pass


class AnomaliStaxxIncidentsException(AnomaliStaxxException):
    pass


class AnomaliStaxxSeverityException(AnomaliStaxxException):
    pass
