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

import base64
import collections
import dataclasses
import json

import requests

from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.validation import ParameterValidator
from TIPCommon.utils import is_empty_string_or_none
from . import constants
from . import AuthenticationManager as auth_manager
from . import HTTPV2Manager as api_manager
from .UtilsManager import convert_to_base_64
from .exceptions import HTTPV2AuthException, HTTPV2HTTPException


IntegrationParams = collections.namedtuple(
    "IntegrationParams", ["auth_params", "api_params"]
)


@dataclasses.dataclass
class ActionParams:
    method: str = None
    url_path: str = None
    url_params: str | dict = None
    headers: str | dict = None
    cookie: str | dict = None
    body_payload: str = None
    expected_response_values: str | dict = None
    follow_redirects: bool = None
    fail_on_error: bool = None
    base64_output: bool = None
    fields_to_return: str = None
    request_timeout: int = None


def get_integration_params(soar_action: SiemplifyAction) -> IntegrationParams:
    """Get HTTP V2 IntegrationParams object for auth params and api params

    Args:
        soar_action (SiemplifyAction): SiemplifyAction object

    Returns:
        IntegrationParams: Named tuple IntegrationParams
    """
    test_url = extract_configuration_param(
        soar_action,
        provider_name=constants.PROVIDER_NAME,
        param_name="Test URL",
        print_value=True,
    )
    basic_auth_username = extract_configuration_param(
        soar_action,
        param_name="Basic Auth Username",
        provider_name=constants.PROVIDER_NAME,
        print_value=True,
    )
    basic_auth_password = extract_configuration_param(
        soar_action,
        param_name="Basic Auth Password",
        provider_name=constants.PROVIDER_NAME,
        remove_whitespaces=False,
    )
    api_key_field_name = extract_configuration_param(
        soar_action,
        provider_name=constants.PROVIDER_NAME,
        param_name="API Key Field Name",
        print_value=True,
    )
    api_key_secret = extract_configuration_param(
        soar_action,
        provider_name=constants.PROVIDER_NAME,
        param_name="API Key Secret",
        remove_whitespaces=False,
    )
    auth_api_request_method = extract_configuration_param(
        soar_action,
        provider_name=constants.PROVIDER_NAME,
        param_name="Dedicated Auth API Request Method",
        print_value=True,
    )
    auth_api_request_url = extract_configuration_param(
        soar_action,
        provider_name=constants.PROVIDER_NAME,
        param_name="Dedicated Auth API Request URL",
        print_value=True,
    )
    auth_api_request_headers = extract_configuration_param(
        soar_action,
        provider_name=constants.PROVIDER_NAME,
        param_name="Dedicated Auth API Request Headers",
        remove_whitespaces=False,
        default_value="{}",
    )
    auth_api_request_body = extract_configuration_param(
        soar_action,
        provider_name=constants.PROVIDER_NAME,
        param_name="Dedicated Auth API Request Body",
        remove_whitespaces=False,
        default_value="{}",
    )
    auth_api_request_token_field_name = extract_configuration_param(
        soar_action,
        provider_name=constants.PROVIDER_NAME,
        param_name="Dedicated Auth API Request Token Field Name",
        print_value=True,
    )
    verify_ssl = extract_configuration_param(
        soar_action,
        provider_name=constants.PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )
    ca_certificate = extract_configuration_param(
        soar_action,
        provider_name=constants.PROVIDER_NAME,
        param_name="CA Certificate",
        print_value=True,
    )

    restrict_domain = extract_configuration_param(
        soar_action,
        provider_name=constants.PROVIDER_NAME,
        param_name="Restrict Domain",
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    auth_params = auth_manager.SessionAuthenticationParameters(
        test_url=test_url,
        basic_auth_username=basic_auth_username,
        basic_auth_password=basic_auth_password,
        api_key_field_name=api_key_field_name,
        api_key_secret=api_key_secret,
        auth_api_request_method=auth_api_request_method,
        auth_api_request_url=auth_api_request_url,
        auth_api_request_headers=auth_api_request_headers,
        auth_api_request_body=auth_api_request_body,
        auth_api_request_token_field_name=auth_api_request_token_field_name,
        restrict_domain=restrict_domain,
        verify_ssl=verify_ssl,
        ca_certificate=ca_certificate,
    )
    api_params = api_manager.ApiParameters(
        test_url=test_url, restrict_domain=restrict_domain
    )
    integration_params = IntegrationParams(
        auth_params=auth_params, api_params=api_params
    )

    return integration_params


def validate_configuration_params(
    soar_action: SiemplifyAction,
    auth_params: auth_manager.SessionAuthenticationParameters,
) -> None:
    """Validate configuration parameters for auth params

    Args:
        soar_action (SiemplifyAction): SiemplifyAction object
        auth_params (auth_manager.SessionAuthenticationParameters): auth params object
    """
    validator = ParameterValidator(soar_action)

    if not is_empty_string_or_none(auth_params.auth_api_request_method):
        validator.validate_ddl(
            param_name="Dedicated Auth API Request Method",
            value=auth_params.auth_api_request_method,
            ddl_values=list(constants.API_REQUEST_METHODS_MAPPING.keys()),
            print_value=True,
        )

    if not is_empty_string_or_none(auth_params.auth_api_request_headers):
        auth_api_request_headers = validator.validate_json(
            param_name="Dedicated Auth API Request Headers",
            json_string=auth_params.auth_api_request_headers,
            print_value=True,
        )

        auth_params.auth_api_request_headers = auth_api_request_headers

    if not is_empty_string_or_none(auth_params.auth_api_request_body):
        auth_api_request_body = validator.validate_json(
            param_name="Dedicated Auth API Request Body",
            json_string=auth_params.auth_api_request_body,
            print_value=True,
        )

        auth_params.auth_api_request_body = auth_api_request_body


def validate_action_params(
    soar_action: SiemplifyAction, action_params: ActionParams
) -> None:
    """Validate action parameters

    Args:
        soar_action (SiemplifyAction): SiemplifyAction object
        action_params (ActionParams): action params
    """
    validator = ParameterValidator(soar_action)

    if not is_empty_string_or_none(action_params.url_params):
        action_params.url_params = validator.validate_json(
            param_name="URL Params",
            json_string=action_params.url_params,
            print_value=True,
        )

    if not is_empty_string_or_none(action_params.headers):
        action_params.headers = validator.validate_json(
            param_name="Headers", json_string=action_params.headers, print_value=True
        )

    if not is_empty_string_or_none(action_params.cookie):
        action_params.cookie = validator.validate_json(
            param_name="Cookie", json_string=action_params.cookie, print_value=True
        )

    if not is_empty_string_or_none(action_params.expected_response_values):
        action_params.expected_response_values = validator.validate_json(
            param_name="Expected Response Values",
            json_string=action_params.expected_response_values,
            print_value=True,
        )

    if not is_empty_string_or_none(action_params.fields_to_return):
        action_params.fields_to_return = validator.validate_csv(
            param_name="Fields To Return",
            csv_string=action_params.fields_to_return,
            possible_values=constants.FIELDS_TO_RETURN_POSSIBLE_VALUES,
            print_value=True,
        )


def get_auth_method(
    auth_params: auth_manager.SessionAuthenticationParameters,
) -> str | None:
    """Determine auth method from auth params

    Args:
        auth_params (auth_manager.SessionAuthenticationParameters): auth params object

    Returns:
        str: auth method
    """
    if (
        not is_empty_string_or_none(auth_params.auth_api_request_method)
        and not is_empty_string_or_none(auth_params.auth_api_request_url)
        and not is_empty_string_or_none(auth_params.auth_api_request_token_field_name)
    ):
        return constants.AUTH_METHOD.get("ACCESS_TOKEN")
    if (
        not is_empty_string_or_none(auth_params.test_url)
        and not is_empty_string_or_none(auth_params.basic_auth_username)
        and not is_empty_string_or_none(auth_params.basic_auth_password)
    ):
        return constants.AUTH_METHOD.get("BASIC")
    if (
        not is_empty_string_or_none(auth_params.test_url)
        and not is_empty_string_or_none(auth_params.api_key_field_name)
        and not is_empty_string_or_none(auth_params.api_key_secret)
    ):
        return constants.AUTH_METHOD.get("API_KEY")

    if (
        is_empty_string_or_none(auth_params.test_url)
        and auth_params.restrict_domain is True
    ):
        raise HTTPV2AuthException(
            "\"Test URL\" parameter of integration configuration doesn’t have a valid "
            "value. Either disable the \"Restrict Domain\" parameter or update the "
            "configuration integration instance. "
        )

    return constants.AUTH_METHOD.get("NO_AUTH")


def validate_response(
    response: requests.Response, error_msg: str = "An error occurred"
) -> None:
    """Validate response

    Args:
        response (requests.Response): Response to validate
        error_msg (str): Default message to display on error

    Raises:
        HTTPV2Exception: If there is any error in the response
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        raise HTTPV2HTTPException(
            f"{error_msg}: {error} {error.response.content}",
            status_code=error.response.status_code,
        ) from error


def get_results_from_response(
    response: requests.Response, fields_to_return: [str], base64_output: bool = False
) -> dict:
    """Get results from response

    Args:
        response (requests.Response): request response
        fields_to_return ([str]): list of fields to return in results
        base64_output (bool): specifies if response data should be converted to base64

    Returns:
        dict: results from response
    """
    try:
        # try to get json from the response
        response_data = response.json()
    except json.JSONDecodeError:
        # response is not in json format, getting response text instead
        response_data = response.text

    results = {
        "response_data": (
            convert_to_base_64(response_data) if base64_output else response_data
        ),
        "redirects": [item.url for item in response.history] + [response.url],
        "response_code": response.status_code,
        "response_cookies": response.cookies.get_dict(),
        "response_headers": dict(response.headers),
        "apparent_encoding": response.apparent_encoding,
    }

    return {key: value for key, value in results.items() if key in fields_to_return}


def prepare_body_payload(body_payload_string: str, headers: dict[str, str]) -> dict:
    """Prepare body payload by identifying payload format, either json, base64 or text

    Args:
        body_payload_string (str): body payload string

    Returns:
        dict: body payload
    """
    content_type = headers.get("Content-Type")
    if content_type is not None and content_type == "application/x-www-form-urlencoded":
        return {"data": json.loads(body_payload_string)}
    try:
        return {"json": json.loads(body_payload_string)}
    except (json.decoder.JSONDecodeError, TypeError):
        try:
            return {"data": base64.b64decode(body_payload_string)}
        except Exception:
            return {"data": body_payload_string}
