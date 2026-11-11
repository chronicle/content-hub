from __future__ import annotations
from scc_enterprise.core.SCCEnterpriseExceptions import SCCEnterpriseManagerException


class SNowException(SCCEnterpriseManagerException):
    """Generic ServiceNow error"""


class SNowNotFoundException(SCCEnterpriseManagerException):
    """Generic Not Found error"""


class SNowTableNotFoundException(SNowNotFoundException):
    """Table was not found (in ServiceNow)"""


class SNowRecordNotFoundException(SNowNotFoundException):
    """Record was not found (in ServiceNow)"""


class SNowPermissionDeniedException(SCCEnterpriseManagerException):
    """Permission denied error"""
