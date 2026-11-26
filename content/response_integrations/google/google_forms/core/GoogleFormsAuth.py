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
from google.oauth2 import service_account

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyJob import SiemplifyJob

from TIPCommon.extraction import extract_script_param
from TIPCommon.rest.auth import get_auth_request
from TIPCommon.types import ChronicleSOAR, SingleJson
from TIPCommon.utils import is_empty_string_or_none
from TIPCommon.validation import ParameterValidator

from .constants import INTEGRATION_NAME, OAUTH_SCOPES
from .exceptions import (
    GoogleFormsAuthenticationError,
    InvalidParameterException,
)
from .utils import parse_string_to_dict


def build_auth_manager_params(chronicle_soar: ChronicleSOAR) -> AuthManagerParams:
    """
    Extract auth params and build Auth manager.

    Args:
         chronicle_soar(ChronicleSOAR): ChronicleSOAR SDK object

    Returns:
        AuthManagerParams: Google Forms params object.
    """
    if isinstance(chronicle_soar, SiemplifyAction):
        input_dictionary = chronicle_soar.get_configuration(INTEGRATION_NAME)
    elif isinstance(chronicle_soar, SiemplifyConnectorExecution):
        input_dictionary = chronicle_soar.parameters
    elif isinstance(chronicle_soar, SiemplifyJob):
        input_dictionary = chronicle_soar.parameters
    else:
        raise InvalidParameterException("Provided SOAR instance is not supported.")

    delegated_email = extract_script_param(
        chronicle_soar,
        input_dictionary=input_dictionary,
        param_name="Delegated Email",
        is_mandatory=True,
        print_value=True,
    )
    service_account_json = extract_script_param(
        chronicle_soar,
        input_dictionary=input_dictionary,
        param_name="Service Account JSON",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_script_param(
        chronicle_soar,
        input_dictionary=input_dictionary,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    validator = ParameterValidator(chronicle_soar)
    if not is_empty_string_or_none(service_account_json):
        service_account_json = validator.validate_json(
            param_name="Service Account Json File Content",
            json_string=service_account_json,
            print_value=False,
        )

    return AuthManagerParams(
        service_account_json=service_account_json,
        delegated_email=delegated_email,
        verify_ssl=verify_ssl,
    )


@dataclasses.dataclass(frozen=True)
class AuthManagerParams:
    delegated_email: str
    service_account_json: str | SingleJson
    verify_ssl: bool

    @property
    def service_account_dict(self) -> SingleJson | None:
        """Service account key's dict."""
        service_account_json_needs_parsing = not is_empty_string_or_none(
            self.service_account_json
        ) and not isinstance(self.service_account_json, dict)
        if service_account_json_needs_parsing:
            return parse_string_to_dict(self.service_account_json)

        return self.service_account_json


class GoogleFormsAuthManager:

    def __init__(
        self,
        params: AuthManagerParams,
    ) -> None:
        self.verify_ssl = params.verify_ssl

        try:
            self.credentials = service_account.Credentials.from_service_account_info(
                info=params.service_account_json,
                scopes=OAUTH_SCOPES,
                subject=params.delegated_email,
            )
            self.credentials.refresh(get_auth_request(verify_ssl=self.verify_ssl))

        except RefreshError as e:
            raise GoogleFormsAuthenticationError(
                "The 'Delegated Email' or 'Service Account JSON' provided is "
                "invalid. Please verify your credentials."
            ) from e

    def prepare_session(self) -> AuthorizedSession:
        """Prepare session object to be used in API session."""
        session = AuthorizedSession(
            self.credentials,
            auth_request=get_auth_request(verify_ssl=self.verify_ssl),
        )
        session.verify = self.verify_ssl

        return session
