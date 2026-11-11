from __future__ import annotations
class VertexAIException(Exception):
    """General exception for Vertex AI."""


class VertexAIValidationException(VertexAIException):
    """General exception for validation errors."""


class VertexAIManagerException(VertexAIException):
    """General exception for Vertex AI API Manager."""


class VertexAIAuthException(VertexAIException):
    """Exception in case of authentication error."""


class VertexAIInvalidJsonException(VertexAIException):
    """Exception in case of invalid JSON string provided."""
