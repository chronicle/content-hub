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
import sys

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_action_param
from ..core import HTTPV2Manager as api_manager
from ..core import AuthenticationManager as auth_manager
from ..core import api_utils
from ..core.UtilsManager import (
    format_dict,
    sava_attachment_to_case_wall,
    validate_expected_values,
)
from ..core.constants import (
    EXECUTE_HTTP_REQUEST_SCRIPT_NAME,
    AUTH_METHOD,
    ACCESS_TOKEN_PLACEHOLDER,
)
from ..core.exceptions import HTTPV2HTTPException, HTTPV2DomainMismatchException


@output_handler
def main(is_first_run):
    soar_action = SiemplifyAction()
    soar_action.script_name = EXECUTE_HTTP_REQUEST_SCRIPT_NAME
    mode = "Main" if is_first_run else "QueryState"
    result_value = False
    status = EXECUTION_STATE_COMPLETED
    action_params = api_utils.ActionParams()

    soar_action.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    try:
        # get integration params
        integration_params = api_utils.get_integration_params(soar_action)
        auth_params = integration_params.auth_params
        api_params = integration_params.api_params

        # validate integration params
        api_utils.validate_configuration_params(
            soar_action=soar_action, auth_params=auth_params
        )
        api_params.auth_method = api_utils.get_auth_method(auth_params)

        # action parameters
        action_params.method = extract_action_param(
            soar_action, param_name="Method", is_mandatory=True, print_value=True
        )
        action_params.url_path = extract_action_param(
            soar_action, param_name="URL Path", is_mandatory=True, print_value=True
        )
        action_params.url_params = extract_action_param(
            soar_action, param_name="URL Params", print_value=True
        )
        action_params.headers = extract_action_param(
            soar_action, param_name="Headers", print_value=True, default_value="{}"
        )
        action_params.cookie = extract_action_param(
            soar_action, param_name="Cookie", print_value=True
        )
        action_params.body_payload = extract_action_param(
            soar_action, param_name="Body Payload", print_value=True
        )
        action_params.expected_response_values = extract_action_param(
            soar_action, param_name="Expected Response Values", print_value=True
        )
        action_params.follow_redirects = extract_action_param(
            soar_action,
            param_name="Follow Redirects",
            input_type=bool,
            print_value=True,
        )
        action_params.fail_on_error = extract_action_param(
            soar_action, param_name="Fail on 4xx/5xx", input_type=bool, print_value=True
        )
        action_params.base64_output = extract_action_param(
            soar_action, param_name="Base64 Output", input_type=bool, print_value=True
        )
        action_params.fields_to_return = extract_action_param(
            soar_action,
            param_name="Fields To Return",
            is_mandatory=True,
            print_value=True,
        )
        action_params.request_timeout = extract_action_param(
            soar_action,
            param_name="Request Timeout",
            is_mandatory=True,
            input_type=int,
            print_value=True,
        )
        action_params.save_to_case_wall = extract_action_param(
            soar_action,
            param_name="Save To Case Wall",
            input_type=bool,
            print_value=True,
        )
        action_params.password_protect_zip = extract_action_param(
            soar_action,
            param_name="Password Protect Zip",
            input_type=bool,
            print_value=True,
        )

        # validate action params
        api_utils.validate_action_params(
            soar_action=soar_action, action_params=action_params
        )

        soar_action.LOGGER.info(f"----------------- {mode} - Started -----------------")

        session, access_token = auth_manager.get_authenticated_session(
            chronicle_soar=soar_action,
            auth_method=api_params.auth_method,
            auth_params=auth_params,
        )
        manager = api_manager.ApiManager(
            session=session, api_params=api_params, logger=soar_action.logger
        )

        if api_params.auth_method == AUTH_METHOD.get("ACCESS_TOKEN"):
            action_params.headers = format_dict(
                action_params.headers or {}, **{ACCESS_TOKEN_PLACEHOLDER: access_token}
            )
        response = manager.execute_http_request(
            method=action_params.method,
            url_path=action_params.url_path,
            params=action_params.url_params,
            headers=action_params.headers,
            cookies=action_params.cookie,
            body_payload=action_params.body_payload,
            follow_redirects=action_params.follow_redirects,
            timeout=action_params.request_timeout,
        )

        results = api_utils.get_results_from_response(
            response=response,
            fields_to_return=action_params.fields_to_return,
            base64_output=action_params.base64_output,
        )

        if results:
            soar_action.result.add_result_json(results)

        api_utils.validate_response(response)

        if action_params.expected_response_values and not validate_expected_values(
            data=results.get("response_data"),
            expected_values=action_params.expected_response_values,
        ):
            output_message = (
                "Successfully executed API request. "
                "Waiting for expected response values."
            )
            status = EXECUTION_STATE_INPROGRESS

        else:
            if action_params.save_to_case_wall:
                sava_attachment_to_case_wall(
                    soar_action=soar_action,
                    response=response,
                    password_protect_zip=action_params.password_protect_zip,
                    logger=soar_action.LOGGER,
                )

            result_value = True
            output_message = "Successfully executed API request."

    except HTTPV2HTTPException as error:
        if not action_params.fail_on_error:
            output_message = (
                "Successfully executed API request, but status code "
                f"{error.status_code} was returned. "
                "Please check the request or try again later."
            )
        else:
            output_message = f"Failed to execute API request. Error: {error}"
            status = EXECUTION_STATE_FAILED

        soar_action.LOGGER.error(output_message)
        soar_action.LOGGER.exception(error)
    except HTTPV2DomainMismatchException as error:
        output_message = (
            "Failed to execute API request. Error: “URL Path” domain "
            "is not aligned with domain provided in the “Test URL” parameter of "
            "integration configuration. Either disable "
            "the “Restrict Domain” parameter"
            " or update the configuration of action or integration instance. "
        )
        soar_action.LOGGER.error(output_message)
        soar_action.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
    except Exception as error:
        output_message = f"Failed to execute API request. Error: {error}"
        soar_action.LOGGER.error(output_message)
        soar_action.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED

    soar_action.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    soar_action.LOGGER.info(
        f"\nstatus: {status}\n"
        f"result_value: {result_value}\n"
        f"output_message: {output_message}"
    )
    soar_action.end(output_message, result_value, status)


if __name__ == "__main__":
    first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(first_run)
