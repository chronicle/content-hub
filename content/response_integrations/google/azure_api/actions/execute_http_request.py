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

from typing import TYPE_CHECKING

import requests

from TIPCommon.extraction import extract_action_param
from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.validation import ParameterValidator
from TIPCommon.utils import is_empty_string_or_none
from ..core import api_utils
from ..core.base_action import BaseAction
from ..core.constants import (
    ERROR_STATUS_CODE_THRESHOLD,
    EXECUTE_HTTP_REQUEST_SCRIPT_NAME,
    FIELDS_TO_RETURN_POSSIBLE_VALUES,
)
from ..core.data_models import ExecuteHTTPRequestParams
from ..core import exceptions
from ..core import utils

if TYPE_CHECKING:
    from typing import Never

    from TIPCommon.types import SingleJson


SUCCESS_MESSAGE: str = "Successfully executed API request."
ERROR_MESSAGE: str = "Failed to execute API request."


class ExecuteHttpRequest(BaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = SUCCESS_MESSAGE
        self.execution_state = ExecutionState.COMPLETED
        self.error_output_message = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        self.params.method = extract_action_param(
            self.soar_action,
            param_name="Method",
            is_mandatory=True,
            print_value=True,
        )
        self.params.url_path = extract_action_param(
            self.soar_action,
            param_name="URL Path",
            is_mandatory=True,
            print_value=True,
        )
        self.params.url_params = extract_action_param(
            self.soar_action,
            param_name="URL Params",
            print_value=True,
        )
        self.params.headers = extract_action_param(
            self.soar_action,
            param_name="Headers",
        )
        self.params.cookie = extract_action_param(
            self.soar_action,
            param_name="Cookie",
        )
        self.params.body_payload = extract_action_param(
            self.soar_action,
            param_name="Body Payload",
        )
        self.params.expected_response_values = extract_action_param(
            self.soar_action,
            param_name="Expected Response Values",
            print_value=True,
        )
        self.params.follow_redirects = extract_action_param(
            self.soar_action,
            param_name="Follow Redirects",
            input_type=bool,
            print_value=True,
        )
        self.params.fail_on_error = extract_action_param(
            self.soar_action,
            param_name="Fail on 4xx/5xx",
            input_type=bool,
            print_value=True,
        )
        self.params.base64_output = extract_action_param(
            self.soar_action,
            param_name="Base64 Output",
            input_type=bool,
            print_value=True,
        )
        self.params.fields_to_return = extract_action_param(
            self.soar_action,
            param_name="Fields To Return",
            is_mandatory=True,
            print_value=True,
        )
        self.params.request_timeout = extract_action_param(
            self.soar_action,
            param_name="Request Timeout",
            is_mandatory=True,
            input_type=int,
            print_value=True,
        )
        self.params.save_to_case_wall = extract_action_param(
            self.soar_action,
            param_name="Save To Case Wall",
            input_type=bool,
            print_value=True,
        )
        self.params.password_protect_zip = extract_action_param(
            self.soar_action,
            param_name="Password Protect Zip",
            input_type=bool,
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_action)

        if not is_empty_string_or_none(self.params.url_params):
            self.params.url_params = validator.validate_json(
                param_name="URL Params",
                json_string=self.params.url_params,
                print_value=True,
            )

        if not is_empty_string_or_none(self.params.headers):
            self.params.headers = validator.validate_json(
                param_name="Headers",
                json_string=self.params.headers,
            )

        if not is_empty_string_or_none(self.params.cookie):
            self.params.cookie = validator.validate_json(
                param_name="Cookie",
                json_string=self.params.cookie,
            )

        if not is_empty_string_or_none(self.params.expected_response_values):
            self.params.expected_response_values = validator.validate_json(
                param_name="Expected Response Values",
                json_string=self.params.expected_response_values,
                print_value=True,
            )

        if not is_empty_string_or_none(self.params.fields_to_return):
            self.params.fields_to_return_list = validator.validate_csv(
                param_name="Fields To Return",
                csv_string=self.params.fields_to_return,
                possible_values=FIELDS_TO_RETURN_POSSIBLE_VALUES,
                print_value=True,
            )

    def _perform_action(self, _: Never) -> None:
        try:
            request_params: ExecuteHTTPRequestParams = ExecuteHTTPRequestParams(
                method=self.params.method,
                url_path=self.params.url_path,
                params=self.params.url_params,
                headers=self.params.headers,
                cookies=self.params.cookie,
                body_payload=self.params.body_payload,
                follow_redirects=self.params.follow_redirects,
                timeout=self.params.request_timeout,
            )
            response: requests.Response = self.api_client.execute_http_request(
                http_request_data=request_params,
            )

            results: SingleJson = utils.get_results_from_response(
                response=response,
                fields_to_return=self.params.fields_to_return,
                base64_output=self.params.base64_output,
            )

            if results:
                self.soar_action.result.add_result_json(results)

            api_utils.validate_response(response)

            wait_for_expected_values: bool = (
                self.params.expected_response_values
                and not utils.validate_expected_values(
                    data=results.get("response_data"),
                    expected_values=self.params.expected_response_values,
                )
            )
            if wait_for_expected_values:
                self.output_message = (
                    "Successfully executed API request. "
                    "Waiting for expected response values."
                )
                self.execution_state = ExecutionState.IN_PROGRESS
                return

            if self.params.save_to_case_wall:
                utils.save_attachment_to_case_wall(
                    soar_action=self.soar_action,
                    response=response,
                    password_protect_zip=self.params.password_protect_zip,
                    logger=self.logger,
                )

        except exceptions.AzureApiHTTPError as error:
            self.logger.error(str(error))
            if (
                self.params.fail_on_error
                and error.status_code >= ERROR_STATUS_CODE_THRESHOLD
            ):
                raise

            self.output_message = (
                "Successfully executed API request, but the status code "
                f"{error.status_code} was returned. Please check the request or "
                "try again later."
            )


def main() -> None:
    ExecuteHttpRequest(EXECUTE_HTTP_REQUEST_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
