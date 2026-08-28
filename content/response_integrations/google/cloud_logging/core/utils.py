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
import json
from collections import namedtuple

from TIPCommon.extraction import extract_configuration_param
from TIPCommon.types import SingleJson, ChronicleSOAR
from TIPCommon.utils import is_empty_string_or_none
from TIPCommon.validation import ParameterValidator

from ..core.consts import API_URL, INTEGRATION_IDENTIFIER
from ..core.exceptions import InvalidJSONFormatException


IntegrationParams = namedtuple(
    "IntegrationParams",
    [
        "api_root",
        "service_account_json",
        "workload_identity_email",
        "project_id",
        "quota_project_id",
        "organization_id",
        "verify_ssl",
    ],
)


# Move to TIPCommon
def parse_string_to_dict(string) -> SingleJson:
    """Parse json string to dict.
    Args:
        string: string to parse.

    Returns:
        {dict} parsed dict.
    """
    try:
        return json.loads(string)
    except json.JSONDecodeError as err:
        error_message = "Unable to parse provided json. Error is:"
        raise InvalidJSONFormatException(f"{error_message} {err}") from err


def get_integration_params(chronicle_soar: ChronicleSOAR) -> IntegrationParams:
    """Returns Integration parameters that are responsible for authentication.
    Args:
        chronicle_soar: Chronicle actio that the params will be extracted from.

    Returns:
        {IntegrationParams} Object that holds the integration parameters.
    """
    api_root = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Root",
        print_value=True,
        default_value=API_URL
    )
    service_account_json = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="User's Service Account",
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )
    workload_identity_email = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Workload Identity Email",
        print_value=True,
    )
    quota_project_id = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Quota Project ID",
        is_mandatory=False,
        print_value=True,
    )
    project_id = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Project ID",
        is_mandatory=False,
        print_value=True,
    )

    organization_id = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Organization ID",
        is_mandatory=False,
        print_value=True,
    )

    service_account_json, workload_identity_email = validate_credentials(
        service_account_json, workload_identity_email, chronicle_soar
    )

    return IntegrationParams(
        api_root=api_root,
        service_account_json=service_account_json,
        workload_identity_email=workload_identity_email,
        quota_project_id=quota_project_id,
        verify_ssl=verify_ssl,
        project_id=project_id,
        organization_id=organization_id,
    )


def validate_credentials(
    users_service_account: str,
    workload_identity_email: str,
    chronicle_soar: ChronicleSOAR,
) -> tuple[str, str]:
    """
    Validates user's service account and workload identity email using
    ParameterValidator.

    Args:
        users_service_account: {str} credentials of the user account in a string format.
        workload_identity_email: {str} workload identity email.
        chronicle_soar: the SOAR action object that we are using for
        validation purposes.

    Returns:
        Validated credentials.

    Raises:
        ParameterValidationError: If one of the credentials is not valid.
    """
    validator = ParameterValidator(chronicle_soar)
    if not is_empty_string_or_none(users_service_account):
        users_service_account = validator.validate_json(
            param_name="User's Service Account",
            json_string=users_service_account,
            print_value=False,
        )
    if not is_empty_string_or_none(workload_identity_email):
        workload_identity_email = validator.validate_email(
            param_name="Workload Identity Email",
            email=workload_identity_email,
            print_value=True,
        )
    return users_service_account, workload_identity_email
