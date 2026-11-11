from __future__ import annotations
class ProofpointCTRError(Exception):
    """
    Base exception for Proofpoint Cloud Threat Response integration.
    """


class ProofpointCTRRateLimitError(Exception):
    """
    Exception raised when API rate limit is exceeded.
    """
