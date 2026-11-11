from __future__ import annotations
class SCCEnterpriseBaseException(Exception):
    """Generic SCC Enterprise exception."""


class SCCEnterpriseManagerException(SCCEnterpriseBaseException):
    """Generic SCC Enterprise Manager exception."""


class ProjectNotFound(SCCEnterpriseBaseException):
    """Project Not Found."""
