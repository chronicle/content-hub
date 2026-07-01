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

from google.auth.transport.requests import AuthorizedSession
from google.auth.exceptions import RefreshError

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyJob import SiemplifyJob
from TIPCommon.adapters import PubSubAdapter
from TIPCommon.base.interfaces import Logger
from TIPCommon.extraction import extract_script_param
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

from ..core.PubSubConstants import INTEGRATION_IDENTIFIER, DEFAULT_OAUTH_SCOPES
from ..core.PubSubExceptions import (
    PubSubAuthException,
    PubSubException,
)
from ..core.PubSubUtils import parse_string_to_dict


def build_auth_manager_params(
        chronicle_soar: ChronicleSOAR
) -> AuthManagerParams:
    """
    Extract auth params for Auth manager.

    Args:
         chronicle_soar: ChronicleSOAR SDK object

    Returns:
        Google Cloud Api Auth manager object
    """
    validator = ParameterValidator(chronicle_soar)

    if hasattr(chronicle_soar, 'get_configuration'):
        input_dictionary = chronicle_soar.get_configuration(INTEGRATION_IDENTIFIER)
    elif hasattr(chronicle_soar, 'parameters'):
        input_dictionary = chronicle_soar.parameters
    elif hasattr(chronicle_soar, 'parameters'):
        input_dictionary = chronicle_soar.parameters
    else:
        raise PubSubException("Provided SOAR instance is not supported.")

    verify_ssl = extract_script_param(
        chronicle_soar,
        input_dictionary=input_dictionary,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True
    )
    project_id = extract_script_param(
        chronicle_soar,
        input_dictionary=input_dictionary,
        param_name="Project ID",
        print_value=True
    )
    quota_project_id = extract_script_param(
        chronicle_soar,
        input_dictionary=input_dictionary,
        param_name="Quota Project ID",
        print_value=True
    )

    service_account_json = extract_script_param(
        chronicle_soar,
        input_dictionary=input_dictionary,
        param_name="Service Account JSON File Content",
        remove_whitespaces=False
    )
    workload_identity_email = extract_script_param(
        chronicle_soar,
        input_dictionary=input_dictionary,
        param_name="Workload Identity Email",
        print_value=True
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
        quota_project_id=quota_project_id,
        service_account_json=service_account_json,
        workload_identity_email=workload_identity_email,
    )


@dataclasses.dataclass(frozen=True)
class AuthManagerParams:
    verify_ssl: bool
    project_id: str | None
    quota_project_id: str | None
    service_account_json: str | SingleJson | None
    workload_identity_email: str | None

    @property
    def service_account_dict(self) -> SingleJson | None:
        """Service account key's dict."""
        service_account_json_needs_parsing = (
            not is_empty_string_or_none(self.service_account_json)
            and not isinstance(self.service_account_json, dict)
        )
        if service_account_json_needs_parsing:
            return parse_string_to_dict(self.service_account_json)

        return self.service_account_json

class AuthManager:
    def __init__(
            self,
            params: AuthManagerParams,
            logger: Logger | None = None,
    ):
        try:
            self.credentials = build_credentials_from_sa(
                user_service_account=params.service_account_dict,
                target_principal=params.workload_identity_email,
                quota_project_id=params.quota_project_id,
                scopes=DEFAULT_OAUTH_SCOPES,
                verify_ssl=params.verify_ssl,
            )
        except RefreshError as e:
            workload_sa_email = get_workload_sa_email("Unknown Principal")
            raise PubSubAuthException(
                "Impersonation is not allowed for the provided service "
                f"account {params.workload_identity_email}. "
                "Please add the \"Service Account Token Creator\" role to the "
                f"service account: {workload_sa_email}"
            ) from e

        self.project_id = (
            params.project_id or
            retrieve_project_id(
                params.service_account_dict,
                params.workload_identity_email
            )
        )
        self.logger = logger
        self.verify_ssl = params.verify_ssl

    def prepare_client(self) -> PubSubAdapter:
        """Preparse session object to be used in API session."""
        session = AuthorizedSession(
            credentials=self.credentials,
            auth_request=get_auth_request(
                verify_ssl=self.verify_ssl
            )
        )
        session.verify = self.verify_ssl
        pub_sub_client = PubSubAdapter(
            session=session,
            project_id=self.project_id,
            logger=self.logger
        )
        return pub_sub_client
