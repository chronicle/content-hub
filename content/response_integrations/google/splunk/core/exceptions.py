from __future__ import annotations
class SplunkException(Exception):
    pass


class SplunkManagerException(SplunkException):
    pass


class SplunkHTTPException(SplunkManagerException):
    pass


class SplunkNotFoundException(SplunkHTTPException):
    pass


class UnableToUpdateNotableEvents(SplunkManagerException):
    pass


class UnableToLoadSourceEvents(SplunkManagerException):
    pass


class SplunkConnectorException(SplunkException):
    pass


class SplunkCaCertificateException(SplunkManagerException):
    pass


class MissingEntityKeysException(Exception):
    def __init__(self, missing_entity_keys):
        self.missing_entity_keys = missing_entity_keys
        super().__init__()


class SplunkBadRequestException(SplunkManagerException):
    pass


class AdhocSearchLevelException(SplunkManagerException):
    pass
