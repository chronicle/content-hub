from __future__ import annotations
class PanoramaException(Exception):
    """
    Common Panorama Exception
    """

    pass


class ResponseObjectNotSet(PanoramaException):
    """
    Exception if response object if None
    """

    pass


class JobNotFinishedException(PanoramaException):
    """
    Exception if job not completed yet
    """

    def __init__(self, progress):
        super(JobNotFinishedException, self).__init__()
        self.progress = progress


class PanoramaConnectivityException(PanoramaException):
    pass


class PanoramaAuthorizationException(PanoramaException):
    pass


class PanoramaAlertsException(PanoramaException):
    pass


class PanoramaSeverityException(PanoramaException):
    pass
