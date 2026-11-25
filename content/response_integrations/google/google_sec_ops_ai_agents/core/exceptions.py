"""Google Chronicle exceptions."""
from __future__ import annotations
INVALID_API_ROOT_ERROR = (
    "API Root should not contain 'backstory'. Please use the 1Platform API root."
)
INVALID_CREDENTIALS_ERROR = "Unable to parse credentials as JSON. Please validate creds"
API_LIMIT_ERROR_MESSAGE = "Reached API request limitation"
UNABLE_TO_CONNECT_ERROR = (
    "Unable to connect to Google Chronicle, please validate your credentials: %s"
)


class ChronicleInvestigationManagerError(Exception):
    """General Exception for Google Chronicle manager."""


class GoogleChronicleAPILimitError(Exception):
    """API Limit Exception for Google Chronicle manager."""


class TriageError(ChronicleInvestigationManagerError):
    """Exception for Triage action."""
