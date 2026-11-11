from __future__ import annotations
from scc_enterprise.core.SCCEnterpriseExceptions import SCCEnterpriseBaseException


class GoogleSecurityCommandCenterException(SCCEnterpriseBaseException):
    """General exception for Google Security Command Center"""


class GoogleSecurityCommandCenterInvalidJsonException(
    GoogleSecurityCommandCenterException
):
    """Exception in case of Invalid JSON"""


class GoogleSecurityCommandCenterInvalidProject(GoogleSecurityCommandCenterException):
    """Exception in case of Invalid Project"""


class GoogleSecurityCommandCenterNotFound(GoogleSecurityCommandCenterException):
    """Exception in case of Not found status"""
