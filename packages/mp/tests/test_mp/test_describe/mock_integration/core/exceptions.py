class SampleIntegrationError(Exception):
    """General exception for Sample Integration."""


class SampleIntegrationInvalidParameterError(SampleIntegrationError):
    """Invalid Parameter error."""


class SampleIntegrationHTTPError(SampleIntegrationError):
    """Exception in case of HTTP error."""

    def __init__(self, message, *args, status_code=None) -> None:
        super().__init__(message, *args)
        self.status_code = status_code


class InvalidRequestParametersError(SampleIntegrationError):
    """Invalid HTTP Requests Parameters Error"""
