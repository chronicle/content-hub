from __future__ import annotations
class ProofPointTapManagerError(Exception):
    """General Exception for ProofPoint TAP manager."""


class InvalidParameterError(Exception):
    """Invalid Parameter Error."""


class ThreatIdNotFoundError(Exception):
    """Threat Id Not Found Error."""


class ProofPointTapNotFoundError(Exception):
    """General error if something is not found in ProofPoint TAP."""
