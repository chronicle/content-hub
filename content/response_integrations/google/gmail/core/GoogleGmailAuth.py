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

import aiohttp

from google.auth.transport._aiohttp_requests import AuthorizedSession

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution

from TIPCommon.extraction import extract_script_param
from TIPCommon.utils import is_empty_string_or_none
from TIPCommon.validation import ParameterValidator

from gmail.core.GoogleGmailConsts import INTEGRATION_IDENTIFIER, OAUTH_SCOPES
from gmail.core.GoogleGmailExceptions import GoogleGmailManagerError
from gmail.core.GoogleGmailUtils import build_workspace_credentials, parse_string_to_dict


def build_auth_manager(
        chronicle_soar: SiemplifyConnectorExecution | SiemplifyAction,
        user_email_address: str,
) -> GoogleGmailAuthManager:
    """
    Extract auth params and build Auth manager.

    Args:
         chronicle_soar: ChronicleSOAR SDK object
         user_email_address: User's email address to use for authentication.
            If None is provided, default one from config will be used instead

    Returns:
        Google Gmail Api manager object
    """
    if hasattr(chronicle_soar, 'get_configuration'):
        input_dictionary = chronicle_soar.get_configuration(INTEGRATION_IDENTIFIER)
    elif hasattr(chronicle_soar, 'parameters'):
        input_dictionary = chronicle_soar.parameters
    else:
        raise GoogleGmailManagerError("Provided SOAR instance is not supported.")

    # Integration configuration
    service_account_json = extract_script_param(
        chronicle_soar,
        input_dictionary=input_dictionary,
        param_name="Service Account JSON File Content",
        remove_whitespaces=False
    )
    verify_ssl = extract_script_param(
        chronicle_soar,
        input_dictionary=input_dictionary,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True
    )
    workload_identity_email = extract_script_param(
        chronicle_soar,
        input_dictionary=input_dictionary,
        param_name="Workload Identity Email",
        print_value=True
    )

    validator = ParameterValidator(chronicle_soar)
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

    return GoogleGmailAuthManager(
        service_account_json=service_account_json,
        workload_identity_email=workload_identity_email,
        delegated_email=user_email_address,
        verify_ssl=verify_ssl
    )


class GoogleGmailAuthManager:
    def __init__(
            self,
            service_account_json: str | dict | None,
            workload_identity_email: str | None,
            delegated_email: str,
            verify_ssl: bool,
    ):
        if (
            not is_empty_string_or_none(service_account_json)
            and not isinstance(service_account_json, dict)
        ):
            service_account_json = parse_string_to_dict(service_account_json)

        self.credentials = build_workspace_credentials(
            workload_identity_email=workload_identity_email,
            service_account_json=service_account_json,
            scopes=OAUTH_SCOPES,
            delegated_email=delegated_email,
            verify_ssl=verify_ssl,
        )
        self.verify_ssl = verify_ssl

    def prepare_session(self) -> AuthorizedSession:
        """Preparse session object to be used in API session."""
        session = AuthorizedSession(
            credentials=self.credentials,
            connector=aiohttp.TCPConnector(
                limit=10,
                limit_per_host=10,
                ssl=(None if self.verify_ssl is True else False),
            ),
            # Allow to fetch proxy set from the env.
            trust_env=True
        )
        return session
