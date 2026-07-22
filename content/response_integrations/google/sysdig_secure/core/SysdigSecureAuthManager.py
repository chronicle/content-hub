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
import requests
from requests import Session

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyJob import SiemplifyJob
from TIPCommon.base.interfaces import Logger
from TIPCommon.extraction import extract_script_param
from TIPCommon.types import ChronicleSOAR

from ..core.SysdigSecureConstants import INTEGRATION_IDENTIFIER
from ..core.SysdigSecureExceptions import SysdigSecureExceptions


def build_auth_manager_params(
        chronicle_soar: ChronicleSOAR
) -> AuthManagerParams:
    """
    Extract auth params for Auth manager

    Args:
         chronicle_soar: ChronicleSOAR SDK object

    Returns:
        AuthManagerParams: AuthManagerParams object
    """
    if isinstance(chronicle_soar, SiemplifyAction):
        input_dictionary = chronicle_soar.get_configuration(INTEGRATION_IDENTIFIER)
    elif isinstance(chronicle_soar, SiemplifyConnectorExecution):
        input_dictionary = chronicle_soar.parameters
    elif isinstance(chronicle_soar, SiemplifyJob):
        input_dictionary = chronicle_soar.parameters
    else:
        raise SysdigSecureExceptions(
            "Provided SOAR instance is not supported."
        )

    api_root = extract_script_param(
        chronicle_soar,
        input_dictionary=input_dictionary,
        param_name="API Root",
        is_mandatory=True,
        print_value=True
    )
    api_token = extract_script_param(
        chronicle_soar,
        input_dictionary=input_dictionary,
        param_name="API Token",
        is_mandatory=True,
        remove_whitespaces=False
    )
    verify_ssl = extract_script_param(
        chronicle_soar,
        input_dictionary=input_dictionary,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True
    )

    return AuthManagerParams(
        api_root=api_root,
        api_token=api_token,
        verify_ssl=verify_ssl
    )


@dataclasses.dataclass(frozen=True)
class AuthManagerParams:
    api_root: str
    api_token: str
    verify_ssl: bool


class AuthManager:
    def __init__(
        self,
        params: AuthManagerParams,
        logger: Logger | None = None,
    ):
        self.api_root = params.api_root
        self.api_token = params.api_token
        self.verify_ssl = params.verify_ssl
        self.logger = logger

    def prepare_session(self) -> Session:
        """Preparse session object to be used in API session."""
        session = requests.session()
        session.verify = self.verify_ssl
        session.headers.update({"Authorization": f"Bearer {self.api_token}"})
        return session
