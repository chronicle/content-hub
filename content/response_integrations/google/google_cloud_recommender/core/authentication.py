from __future__ import annotations

import google.auth.credentials
import google.auth.exceptions
import google_auth_httplib2
import httplib2

import TIPCommon.rest.auth
import TIPCommon.rest.gcp
from TIPCommon.types import SingleJson
from google_cloud_recommender.core import exceptions


def create_resource_name(
    project_id: str,
    organization_id: str,
    user_service_account: SingleJson | None,
    workload_identity_email: str,
) -> str:
    """Get resource name for GCP integrations based on project or organization ID

    Creates the resource based on granularity.
    If there's project ID use it, else if there's org ID use it instead.
    If there's no project ID or org ID get the project ID from the service account
    or workload identity email. If it cant find anything it raises an error.

    Args:
        project_id: The project ID to use
        organization_id: The organization ID to use
        user_service_account: The user's service account to fetch project ID if missing
        workload_identity_email: The email to use to fetch project ID if missing

    Returns:
        The resource name
    """
    if project_id:
        return f"projects/{project_id}"

    if organization_id:
        return f"organizations/{organization_id}"

    project_id = TIPCommon.rest.gcp.retrieve_project_id(
        user_service_account=user_service_account,
        service_account_email=workload_identity_email,
    )
    return f"projects/{project_id}"


# TODO: The repetition is done so we could mock this in the tests.
#   A better design would be to let the manager get a session object in init and not
#   handle authentication. This should be done in a separate class that would create an
#   authenticated session using all the parameters and pass that with the api root when
#   creating the manager.
#   This will enable us to test the manager more easily without
#   repeating code and mock parts of it that do the authentication by themselves by
#   passing a mock session object that can be used across integrations.
#   Also it will make that the manager will be responsible only on creating an sdk to
#   the 3rd party integration (api manager) and not authentication as well
#   (auth manager) helping with separation of concerns.
def create_session(
    credentials: google.auth.credentials.Credentials, verify_ssl: bool
) -> httplib2.Http | google_auth_httplib2.AuthorizedHttp:
    return TIPCommon.rest.gcp.get_http_client(credentials, verify_ssl)


def get_authentication_credentials_or_raise_error(
    user_service_account: SingleJson | None,
    workload_identity_email: str,
    quota_project_id: str,
    verify_ssl: bool,
) -> google.auth.credentials.Credentials:
    """Create Workload Identity credentials. If not possible, raise an error

    Args:
        user_service_account: The user's service account
        workload_identity_email: The workload identity email
        quota_project_id: The quota project ID to use for billing the account
        verify_ssl: Whether to verify SSL when refreshing the token when creating creds

    Returns:
        Authentication credentials
    """
    if user_service_account is not None:
        credentials = _get_credentials_using_service_account(
            user_service_account=user_service_account,
            quota_project_id=quota_project_id,
            verify_ssl=verify_ssl,
        )

    elif workload_identity_email:
        credentials = _get_credentials_using_workload_identity_email(
            workload_identity_email=workload_identity_email,
            quota_project_id=quota_project_id,
            verify_ssl=verify_ssl,
        )

    else:
        raise exceptions.GoogleCloudRecommenderValidationError(
            "Please fill either 'Service Account Json File Content', "
            "'Workload Identity Email' or all other parameters"
        )

    return credentials


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
    try:
        # TODO: Check about including this repeated logic inside
        #  build_credentials_from_sa
        return TIPCommon.rest.auth.build_credentials_from_sa(
            target_principal=workload_identity_email,
            quota_project_id=quota_project_id,
            verify_ssl=verify_ssl,
        )
    except google.auth.exceptions.RefreshError as e:
        workload_sa = TIPCommon.rest.gcp.get_workload_sa_email("Unknown Principal")
        raise exceptions.GoogleCloudRecommenderError(
            "Impersonation is not allowed for the provided service "
            f"account {workload_identity_email}. "
            'Please add the "Service Account Token Creator" role to the '
            f"service account: {workload_sa}"  # TODO: Check if it's okay to print
        ) from e
