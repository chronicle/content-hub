from __future__ import annotations
class GoogleBigQueryManagerError(Exception):
    """General Exception for Google BigQuery manager"""


class GoogleBigQueryValidationError(GoogleBigQueryManagerError):
    """General Validation Error raised in Google BigQuery Integration"""
