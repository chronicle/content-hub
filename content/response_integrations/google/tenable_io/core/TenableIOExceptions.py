from __future__ import annotations
class TenableIOException(Exception):
    """
    General exception for TenableIO
    """

    pass


class ExportNotFinishedException(TenableIOException):
    pass


class EndpointNotFoundException(TenableIOException):
    pass


class WrongScanException(TenableIOException):
    pass


class AssetExportException(TenableIOException):
    """
    Exception for asset export process
    """
