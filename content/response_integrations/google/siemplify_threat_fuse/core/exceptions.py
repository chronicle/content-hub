from __future__ import annotations
class ThreatFuseStatusCodeException(Exception):
    """
    Status Code exception for Siemplify ThreatFuse
    """

    pass


class ThreatFuseValidationException(Exception):
    """
    Validation exception for Siemplify ThreatFuse
    """

    pass


class ThreatFuseNotFoundException(Exception):
    """
    Not Found exception for Siemplify ThreatFuse
    """

    pass


class ThreatFuseIndicatorsNotFoundException(Exception):
    """
    Indicators not found exception for Siemplify ThreatFuse
    """

    pass


class ThreatFuseInvalidCredentialsException(Exception):
    """
    Invalid Credentials exception for Siemplify ThreatFuse
    """

    pass


class ThreatFuseBadRequestException(Exception):
    """
    Bad Request exception for Siemplify ThreatFuse
    """

    pass
