from __future__ import annotations


class ServiceNowException(Exception):
    """
    General Exception for ServiceNow manager
    """

    pass


class ServiceNowConnectorException(Exception):
    """
    Service Now Connector Exception
    """

    pass


class ServiceNowNotFoundException(ServiceNowException):
    pass


class ServiceNowIncidentNotFoundException(ServiceNowNotFoundException):
    pass


class ServiceNowRecordNotFoundException(ServiceNowNotFoundException):
    pass


class ServiceNowTableNotFoundException(ServiceNowNotFoundException):
    pass


class FolderNotFoundException(ServiceNowNotFoundException):
    pass


class UploadAttachmentACLException(ServiceNowException):
    pass


class ClassNotFoundException(ServiceNowNotFoundException):
    pass


class CINotFoundException(ServiceNowException):
    pass


class AttachmentExistsException(ServiceNowException):
    pass


class ChildIncidentsNotExists(ServiceNowException):
    pass


class InvalidParameterException(ServiceNowException):
    """Exception in case of Invalid Parameter values provided."""


class AssignmentGroupNotFoundError(ServiceNowException):
    """Exception in case of Assignment Group not found."""


class AgentError(ServiceNowException):
    """Exception in case of Error in the agent."""
