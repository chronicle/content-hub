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

from google.auth.transport.requests import AuthorizedSession
from google.auth.exceptions import RefreshError

from TIPCommon.extraction import extract_configuration_param
from TIPCommon.rest.auth import (
    build_credentials_from_sa,
    get_auth_request,
)
from TIPCommon.rest.gcp import (
    get_workload_sa_email,
    retrieve_project_id,
)
from TIPCommon.types import ChronicleSOAR
from TIPCommon.utils import is_empty_string_or_none
from TIPCommon.validation import ParameterValidator

from google_cloud_api.core.GoogleCloudApiConstants import INTEGRATION_IDENTIFIER, DEFAULT_OAUTH_SCOPES
from google_cloud_api.core.GoogleCloudApiExceptions import GoogleCloudApiAuthException
from google_cloud_api.core.GoogleCloudApiUtils import parse_string_to_dict


def build_auth_manager(
        chronicle_soar: ChronicleSOAR
) -> AuthManager:
    """
    Extract auth params and build Auth manager.

    Args:
         chronicle_soar: ChronicleSOAR SDK object

    Returns:
        Google Cloud Api Auth manager object
    """
    validator = ParameterValidator(chronicle_soar)

    # Integration configuration
    verify_ssl = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True
    )
    project_id = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Project ID",
        print_value=True
    )
    quota_project_id = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Quota Project ID",
        print_value=True
    )

    service_account_json = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Service Account Json File Content",
        remove_whitespaces=False
    )
    workload_identity_email = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Workload Identity Email",
        print_value=True
    )
    oauth_scopes = validator.validate_csv(
        param_name="OAuth Scopes",
        csv_string=extract_configuration_param(
            chronicle_soar,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="OAuth Scopes",
            default_value=DEFAULT_OAUTH_SCOPES
        )
    )

    if not is_empty_string_or_none(service_account_json):
        service_account_json = validator.validate_json(
            param_name="Service Account Json File Content",
            json_string=service_account_json,
            print_value=False,
        )
    if not is_empty_string_or_none(workload_identity_email):
        workload_identity_email = validator.validate_email(
            param_name="Workload Identity Email",
            email=workload_identity_email,
            print_value=True,
        )

    return AuthManager(
        oauth_scopes=oauth_scopes,
        verify_ssl=verify_ssl,
        project_id=project_id,
        quota_project_id=quota_project_id,
        service_account_json=service_account_json,
        workload_identity_email=workload_identity_email,
    )


class AuthManager:
    def __init__(
            self,
            oauth_scopes: list[str],
            verify_ssl: bool,
            project_id: str | None = None,
            quota_project_id: str | None = None,
            service_account_json: str | dict | None = None,
            workload_identity_email: str | None = None,
    ):
        if (
            not is_empty_string_or_none(service_account_json)
            and not isinstance(service_account_json, dict)
        ):
            service_account_json = parse_string_to_dict(service_account_json)

        try:
            self.credentials = build_credentials_from_sa(
                user_service_account=service_account_json,
                target_principal=workload_identity_email,
                quota_project_id=quota_project_id,
                scopes=oauth_scopes,
                verify_ssl=verify_ssl,
            )
        except RefreshError as e:
            workload_sa_email = get_workload_sa_email("Unknown Principal")
            raise GoogleCloudApiAuthException(
                "Impersonation is not allowed for the provided service "
                f"account {workload_identity_email}. "
                "Please add the \"Service Account Token Creator\" role to the "
                f"service account: {workload_sa_email}"
            ) from e

        self.project_id = retrieve_project_id(
            service_account_json,
            workload_identity_email,
            default_project_id=project_id
        )
        self.verify_ssl = verify_ssl

    def prepare_session(self) -> AuthorizedSession:
        """Preparse session object to be used in API session."""
        session = AuthorizedSession(
            self.credentials,
            auth_request=get_auth_request(
                verify_ssl=self.verify_ssl
            )
        )
        session.verify = self.verify_ssl
        return session
