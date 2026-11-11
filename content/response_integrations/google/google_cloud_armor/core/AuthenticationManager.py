from __future__ import annotations

import dataclasses
import google.auth.credentials
import google.auth.exceptions
import google_auth_httplib2
import httplib2

import TIPCommon.rest.auth
import TIPCommon.rest.gcp
from TIPCommon.types import SingleJson
from google_cloud_armor.core import exceptions


@dataclasses.dataclass
class SessionAuthenticationParameters:
    api_root: str
    project_id: str
    workload_identity_email: str
    user_service_account: str
    verify_ssl: bool


def get_authenticated_session(
    credentials: google.auth.credentials.Credentials, verify_ssl: bool
) -> httplib2.Http | google_auth_httplib2.AuthorizedHttp:
    return TIPCommon.rest.gcp.get_http_client(credentials, verify_ssl)


def get_authentication_credentials_or_raise_error(
    session_parameters: SessionAuthenticationParameters,
) -> google.auth.credentials.Credentials:
    """Create Workload Identity credentials. If not possible, raise an error

    Args:
        session_parameters (SessionAuthenticationParameters):
            SessionAuthenticationParameters object.

    Returns:
        google.auth.credentials.Credentials: Authentication credentials.
    """
    if session_parameters.user_service_account is not None:
        return _get_credentials_using_service_account(
            user_service_account=session_parameters.user_service_account,
            quota_project_id=session_parameters.project_id,
            verify_ssl=session_parameters.verify_ssl,
        )

    if session_parameters.workload_identity_email:
        return _get_credentials_using_workload_identity_email(
            workload_identity_email=session_parameters.workload_identity_email,
            quota_project_id=session_parameters.project_id,
            verify_ssl=session_parameters.verify_ssl,
        )

    raise exceptions.GoogleCloudArmorValidationError(
        "Please fill either 'Service Account Json File Content', "
        "'Workload Identity Email' or all other parameters"
    )


def _get_credentials_using_service_account(
    user_service_account: SingleJson, quota_project_id: str, verify_ssl: bool
) -> google.auth.credentials.Credentials:
    return TIPCommon.rest.auth.build_credentials_from_sa(
        user_service_account=user_service_account,
        quota_project_id=quota_project_id,
        verify_ssl=verify_ssl,
    )


def _get_credentials_using_workload_identity_email(
    workload_identity_email: str, quota_project_id: str, verify_ssl: bool
) -> google.auth.credentials.Credentials:
    """Get credentials using workload identity email.

    Args:
        workload_identity_email (str): workload identity email.
        quota_project_id (str): project id.
        verify_ssl (bool): verify SSL.

    Raises:
        exceptions.GoogleCloudArmorError: when exception occurred while getting
            credentials.

    Returns:
        google.auth.credentials.Credentials: Authentication credentials.
    """
    try:
        #  build_credentials_from_sa
        return TIPCommon.rest.auth.build_credentials_from_sa(
            target_principal=workload_identity_email,
            quota_project_id=quota_project_id,
            verify_ssl=verify_ssl,
        )
    except google.auth.exceptions.RefreshError as e:
        workload_sa = TIPCommon.rest.gcp.get_workload_sa_email("Unknown Principal")
        raise exceptions.GoogleCloudArmorError(
            "Impersonation is not allowed for the provided service "
            f"account {workload_identity_email}. "
            'Please add the "Service Account Token Creator" role to the '
            f"service account: {workload_sa}"
        ) from e


def create_resource_name(
    project_id: str,
    user_service_account: SingleJson | None,
    workload_identity_email: str,
) -> str:
    """Get resource name for GCP integrations based on project or organization ID

    Creates the resource based on granularity.
    If there's project ID use it, else if there's org ID use it instead.
    If there's no project ID or org ID get the project ID from the service account
    or workload identity email. If it can't find anything it raises an error.

    Args:
        project_id: The project ID to use
        organization_id: The organization ID to use
        user_service_account: The user's service account to fetch project ID if missing
        workload_identity_email: The email to use to fetch project ID if missing

    Returns:
        The resource name
    """
    if project_id:
        return f"{project_id}"

    project_id = TIPCommon.rest.gcp.retrieve_project_id(
        user_service_account=user_service_account,
        service_account_email=workload_identity_email,
    )

    return f"{project_id}"
