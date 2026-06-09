# Copyright 2026 Google LLC
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

from typing import TYPE_CHECKING, NamedTuple

import google.auth
import google.auth.impersonated_credentials
import google.auth.transport.requests
import requests
import requests.adapters
import yaml
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyJob import SiemplifyJob
from TIPCommon.extraction import extract_script_param

from .constants import (
    INTEGRATION_IDENTIFIER,
    PROJECT_ID_PARAM,
    SECRET_MANAGER_SCOPE,
    SERVICE_ACCOUNT_JSON_PARAM,
    VERIFY_SSL_PARAM,
    WORKLOAD_IDENTITY_EMAIL_PARAM,
)
from .exceptions import InvalidConfigurationError, SecretManagerError

if TYPE_CHECKING:
    from TIPCommon.types import ChronicleSOAR


class IntegrationParameters(NamedTuple):
    service_account_json: str | None
    project_id: str | None
    workload_identity_email: str | None
    verify_ssl: bool


def build_auth_params(soar_sdk_object: ChronicleSOAR) -> IntegrationParameters:
    """Extract authentication parameters from the SOAR SDK object.

    Detects the SDK class type to determine where to read the
    integration configuration from, then returns a typed
    ``IntegrationParameters`` tuple.

    Args:
        soar_sdk_object: A ChronicleSOAR SDK object (action, connector,
            or job).

    Returns:
        IntegrationParameters: The extracted integration parameters.

    Raises:
        SecretManagerError: If the provided SDK object type is not
            supported.

    """
    sdk_class: str = type(soar_sdk_object).__name__
    if sdk_class == SiemplifyAction.__name__:
        input_dictionary: dict = soar_sdk_object.get_configuration(INTEGRATION_IDENTIFIER)
    elif sdk_class in {
        SiemplifyConnectorExecution.__name__,
        SiemplifyJob.__name__,
    }:
        input_dictionary = soar_sdk_object.parameters
    else:
        msg: str = f"Provided SOAR instance is not supported! type: {sdk_class}."
        raise SecretManagerError(msg)

    service_account_json: str | None = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name=SERVICE_ACCOUNT_JSON_PARAM,
        is_mandatory=False,
        print_value=False,
    )
    project_id: str | None = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name=PROJECT_ID_PARAM,
        is_mandatory=False,
        print_value=True,
    )
    workload_identity_email: str | None = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name=WORKLOAD_IDENTITY_EMAIL_PARAM,
        is_mandatory=False,
        print_value=True,
    )
    verify_ssl: bool = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name=VERIFY_SSL_PARAM,
        is_mandatory=False,
        input_type=bool,
        default_value=True,
        print_value=True,
    )

    return IntegrationParameters(
        service_account_json=service_account_json,
        project_id=project_id,
        workload_identity_email=workload_identity_email,
        verify_ssl=verify_ssl,
    )


def _get_credentials_using_service_account(
    service_account_json: str,
    project_id: str | None = None,
) -> tuple[service_account.Credentials, str | None]:
    """Build credentials from a Service Account JSON key string.

    Args:
        service_account_json: The JSON key string.
        project_id: Explicit project ID, or None to infer.

    Returns:
        A (credentials, project_id) tuple.

    Raises:
        InvalidConfigurationError: If the JSON is malformed.

    """
    try:
        info: dict = yaml.safe_load(service_account_json)
        if not isinstance(info, dict):
            msg: str = "Invalid Service Account: JSON is empty or invalid."
            raise InvalidConfigurationError(msg)
    except yaml.YAMLError as e:
        msg = f"Invalid Service Account YAML/JSON provided: {e}"
        raise InvalidConfigurationError(msg) from e

    creds = service_account.Credentials.from_service_account_info(info)
    credentials = creds.with_scopes([SECRET_MANAGER_SCOPE])
    resolved_project_id: str | None = project_id or info.get("project_id")

    return credentials, resolved_project_id


def _get_credentials_using_workload_identity_email(
    workload_identity_email: str,
) -> google.auth.impersonated_credentials.Credentials:
    """Build impersonated credentials using Application Default Credentials.

    Args:
        workload_identity_email: The service account email to impersonate.

    Returns:
        Impersonated credentials scoped for Secret Manager.

    Raises:
        InvalidConfigurationError: If ADC cannot be resolved.

    """
    try:
        source_credentials, _ = google.auth.default(scopes=[SECRET_MANAGER_SCOPE])
    except google.auth.exceptions.DefaultCredentialsError as e:
        msg: str = f"Could not resolve Application Default Credentials for Workload Identity impersonation: {e}"
        raise InvalidConfigurationError(msg) from e

    return google.auth.impersonated_credentials.Credentials(
        source_credentials=source_credentials,
        target_principal=workload_identity_email,
        target_scopes=[SECRET_MANAGER_SCOPE],
    )


def get_credentials(
    service_account_json: str | None = None,
    project_id: str | None = None,
    workload_identity_email: str | None = None,
) -> tuple[google.auth.credentials.Credentials, str | None]:
    """Get Google credentials and project ID based on the provided parameters.

    Args:
        service_account_json: The Service Account JSON key string.
        project_id: The Google Cloud Project ID.
        workload_identity_email: The service account email to impersonate.

    Returns:
        A (credentials, project_id) tuple.

    Raises:
        InvalidConfigurationError: If configuration is invalid.

    """
    if workload_identity_email:
        credentials = _get_credentials_using_workload_identity_email(workload_identity_email)
        return credentials, project_id

    if service_account_json:
        return _get_credentials_using_service_account(service_account_json, project_id)

    msg = (
        "Either 'Service Account JSON' or 'Workload Identity Email' "
        "must be provided to authenticate with Secret Manager."
    )
    raise InvalidConfigurationError(msg)


def prepare_auth_request(*, verify_ssl: bool = True) -> google.auth.transport.requests.Request:
    """Prepare an auth request for credential token refresh.

    Args:
        verify_ssl (bool): Whether to verify SSL certificates
            on the underlying session. Defaults to True.

    Returns:
        google.auth.transport.requests.Request: An auth request
            configured with the given SSL verification setting.

    """
    auth_request_session = requests.Session()
    auth_request_session.verify = verify_ssl

    retry_adapter = requests.adapters.HTTPAdapter(max_retries=3)
    auth_request_session.mount("https://", retry_adapter)

    return google.auth.transport.requests.Request(session=auth_request_session)


def create_authorized_session(
    credentials: google.auth.credentials.Credentials,
    *,
    verify_ssl: bool = True,
) -> AuthorizedSession:
    """Create an authorized REST session.

    Uses ``prepare_auth_request`` to configure the OAuth2 token
    refresh call with the given SSL verification setting.

    Args:
        credentials: The Google credentials to authorize the session with.
        verify_ssl (bool): Whether to verify SSL certificates.
            Defaults to True.

    Returns:
        AuthorizedSession: An authorized session configured with
            the given SSL verification setting.

    """
    auth_request = prepare_auth_request(verify_ssl=verify_ssl)
    session = AuthorizedSession(credentials, auth_request=auth_request)
    session.verify = verify_ssl

    return session
