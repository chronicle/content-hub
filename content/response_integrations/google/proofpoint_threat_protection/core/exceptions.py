from __future__ import annotations
class ProofpointTPError(Exception):
    """
    Base exception for Proofpoint Threat Protection integration.
    """


class ProofpointTPRateLimitError(Exception):
    """
    Exception raised when API rate limit is exceeded.
    """
