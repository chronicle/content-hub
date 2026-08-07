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

import dataclasses

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import AuthorizedSession
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.rest.auth import (
    build_credentials_from_sa,
    get_auth_request,
)
from TIPCommon.rest.gcp import (
    get_workload_sa_email,
    retrieve_project_id,
)
from TIPCommon.types import ChronicleSOAR, SingleJson
from TIPCommon.utils import is_empty_string_or_none
from TIPCommon.validation import ParameterValidator
from ..core.VertexAIConstants import INTEGRATION_IDENTIFIER, OAUTH_SCOPES
from ..core.VertexAIExceptions import VertexAIAuthException
from ..core.VertexAIUtils import parse_string_to_dict


def build_auth_manager_params(chronicle_soar: ChronicleSOAR) -> AuthManagerParams:
    """Extract auth params.

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
        print_value=True,
    )
    project_id = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Project ID",
        print_value=True,
    )

    service_account_json = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Service Account Json File Content",
        remove_whitespaces=False,
    )
    workload_identity_email = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Workload Identity Email",
        print_value=True,
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

    return AuthManagerParams(
        verify_ssl=verify_ssl,
        project_id=project_id,
        service_account_json=service_account_json,
        workload_identity_email=workload_identity_email,
    )


@dataclasses.dataclass(frozen=True, slots=True)
class AuthManagerParams:
    verify_ssl: bool
    project_id: str
    service_account_json: str | SingleJson | None
    workload_identity_email: str | None

    @property
    def service_account_dict(self) -> SingleJson:
        """Service account key's dict."""
        service_account_json_needs_parsing = not is_empty_string_or_none(
            self.service_account_json,
        ) and not isinstance(self.service_account_json, dict)
        if service_account_json_needs_parsing:
            return parse_string_to_dict(self.service_account_json)

        return self.service_account_json


class AuthManager:
    def __init__(
        self,
        auth_params: AuthManagerParams,
    ):
        try:
            self.credentials = build_credentials_from_sa(
                user_service_account=auth_params.service_account_json,
                target_principal=auth_params.workload_identity_email,
                scopes=OAUTH_SCOPES,
                verify_ssl=auth_params.verify_ssl,
            )
        except RefreshError as e:
            workload_sa_email = get_workload_sa_email("Unknown Principal")
            raise VertexAIAuthException(
                "Impersonation is not allowed for the provided service "
                f"account {auth_params.workload_identity_email}. "
                'Please add the "Service Account Token Creator" role to the '
                f"service account: {workload_sa_email}",
            ) from e

        self.project_id = retrieve_project_id(
            auth_params.service_account_json,
            auth_params.workload_identity_email,
            default_project_id=auth_params.project_id,
        )
        self.verify_ssl = auth_params.verify_ssl

    def prepare_session(self) -> AuthorizedSession:
        """Preparse session object to be used in API session."""
        session = AuthorizedSession(
            self.credentials, auth_request=get_auth_request(verify_ssl=self.verify_ssl),
        )
        session.verify = self.verify_ssl
        return session
