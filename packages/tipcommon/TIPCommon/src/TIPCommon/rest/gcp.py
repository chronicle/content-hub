# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import re
from typing import Union

import google_auth_httplib2
import httplib2
import requests
from google.oauth2 import service_account
from googleapiclient import _auth

from ..exceptions import (
    GoogleCloudException,
    ImpersonationUnauthorizedError,
    NotFoundError,
)
from ..types import SingleJson
from ..utils import is_empty_string_or_none


class GcpPermissions:
    """ GCP Permissions constants namespace

        keep the attribute names format to PRODUCT_RESOURCE_PERMISSION
        example: IAM_SA_GET_ACCESS_TOKEN
    """
    # pylint: disable=invalid-name
    IAM_SA_GET_ACCESS_TOKEN = "iam.serviceAccounts.getAccessToken"


class GcpErrorReason:
    """ GCP Error Reason constants namespace
    """
    # pylint: disable=invalid-name
    IAM_PERMISSION_DENIED = "IAM_PERMISSION_DENIED"


def get_http_client(
        credentials: service_account.Credentials,
        verify_ssl: bool = True
    ) -> Union[httplib2.Http, google_auth_httplib2.AuthorizedHttp]:
    """Get GCP Authorized http client

    Args:
        credentials (service_account.Credentials): GCP Credentials object
        verify_ssl (bool, optional): Verify SSL certificate. Defaults to True.

    Returns:
        Union[httplib2.Http, google_auth_httplib2.AuthorizedHttp]: _description_
    """
    http_client = _auth.authorized_http(credentials)
    http_client.http.disable_ssl_certificate_validation = not verify_ssl
    return http_client


def retrieve_project_id(
        user_service_account: SingleJson | None,
        service_account_email: str | None,
        default_project_id: str | None = None
) -> str | None:
    """Get project id from service account or workload identity email

    Args:
        user_service_account (SingleJson | None): User service account json
        service_account_email (str | None): Workload identity email
        default_project_id(str | None):
            Default project id to return if not found.
            If provided, this function will not raise NotFoundError.
            Defaults to None.


    raises:
        NotFoundError: Could not parse the project name ouf of the SA email

    Returns:
        str | None:
            Project id of the service account or workload identity email.
            If not found, returns None.
    """
    try:
        if not is_empty_string_or_none(user_service_account):
            return extract_project_id_from_sa_key(user_service_account)
        if not is_empty_string_or_none(service_account_email):
            return extract_project_id_from_sa_email(service_account_email)
    except NotFoundError:
        if default_project_id is None:
            raise

    return default_project_id


def extract_project_id_from_sa_key(service_account_json: SingleJson) -> str:
    """Extract the project id from the service account json key.

    Args:
        service_account_json (SingleJson): Service Account json key

    Raises:
        NotFoundError: Could not find "project_id" field in the Service Account key

    Returns:
        str: project_id field from the service account key
    """
    empty = object()
    project_id = service_account_json.get("project_id", empty)
    if project_id is empty:
        raise NotFoundError(
            "Project ID could not be found in Service Account key"
        )
    return project_id


def extract_project_id_from_sa_email(service_account_email: str) -> str:
    """Extract the project id from the service account email.

    Args:
        service_account_email (str): The service account email.

    Returns:
        str: The project id.

    raises:
        NotFoundError: Could not parse the project name ouf of the SA email
    """
    try:
        res = re.findall(r"@([\w0-9\-_]+).", service_account_email)
        return res[0]
    except (TypeError, IndexError) as e:
        raise NotFoundError(
            "Project name could not be found in Service Account email: "
            f"{str(service_account_email)}"
        ) from e


def validate_impersonation(
        content: dict,
        default_error_msg: str = "Service Account Impersonation failed"
    ) -> None:
    """Validate Service Account impersonation from http authorized response

    Note that this function will raise ImpersonationUnauthorizedError only if
    SA impersonation is not authorized. Otherwise, it will return None.

    Args:
        content (dict): http authorized Response content
        default_error_msg (str, optional):
            error message to raise if not found in response content.
            Defaults to "Service Account Impersonation failed".

    Raises:
        ImpersonationUnauthorizedError:
            Service Account impersonation is not authorized.
    """
    error_msg = content.get("error", {}).get("message", default_error_msg)
    error_details = content.get("error", {}).get("details", [])
    if error_details:
        reason = error_details[0].get("reason", "")
        permission = error_details[0].get("metadata", {}).get("permission", "")
        if (
                reason == GcpPermissions.IAM_SA_GET_ACCESS_TOKEN and
                permission == GcpErrorReason.IAM_PERMISSION_DENIED
        ):
            raise ImpersonationUnauthorizedError(f"{reason} - {error_msg}")


def get_workload_sa_email(default_sa_to_return: str | None = None) -> str:
    """ Retrieves the Workload service account email from GCP metadata server

    Args:
        default_sa_to_return (str | None):
            Default service account to return if not found.
            Defaults to None.

    Raises:
        GoogleCloudException: Could not get GCP Workload service Account email

    Returns:
        str: Workload service account email
    """
    metadata_server_url = (
        "http://metadata.google.internal/computeMetadata"
        "/v1/instance/service-accounts/default/email"
    )
    headers = {"Metadata-Flavor": "Google"}
    response = requests.get(metadata_server_url, headers=headers)
    try:
        response.raise_for_status()
        return response.text or default_sa_to_return
    except requests.HTTPError as e:
        if default_sa_to_return is not None:
            return default_sa_to_return
        raise GoogleCloudException(
            f"Could not get GCP Workload service Account email. Error: {e}"
        ) from e
