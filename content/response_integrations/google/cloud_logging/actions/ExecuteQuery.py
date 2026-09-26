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
from datetime import datetime

from TIPCommon.base.action import Action
from TIPCommon import validation
from TIPCommon.extraction import extract_action_param
from ..core import consts
from ..core.exceptions import CloudLoggingManagerError
from ..core.CloudLoggingApiManager import CloudLoggingApiManager
from ..core.CloudLoggingAuthManager import build_api_manager_params, build_auth_manager


class ExecuteQuery(Action):

    def __init__(self) -> None:
        super().__init__(consts.EXECUTE_QUERY_SCRIPT_NAME)
        self.json_results = []
        self.result_value = True
        self.output_message = ""
        self.error_output_message = (
            f'Error executing action "{consts.EXECUTE_QUERY_SCRIPT_NAME}".'
        )

    def _extract_action_parameters(self) -> None:

        # Action Parameters
        self.params.query = extract_action_param(
            self.soar_action,
            param_name="Query",
            is_mandatory=True,
            print_value=True,
        )
        self.params.project_id = extract_action_param(
            self.soar_action,
            param_name="Project ID",
            print_value=True,
        )
        self.params.organization_id = extract_action_param(
            self.soar_action,
            param_name="Organization ID",
            print_value=True,
        )
        self.params.time_frame = extract_action_param(
            self.soar_action,
            param_name="Time Frame",
            print_value=True,
        )
        self.params.start_time = extract_action_param(
            self.soar_action,
            param_name="Start Time",
            print_value=True,
        )
        self.params.end_time = extract_action_param(
            self.soar_action,
            param_name="End Time",
            print_value=True,
        )
        self.params.max_records = extract_action_param(
            self.soar_action,
            param_name="Max Records To Return",
            input_type=int,
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator = validation.ParameterValidator(self.soar_action)
        self.params.time_frame = validator.validate_ddl(
            "Time Frame",
            self.params.time_frame,
            [*consts.TIME_INTERVALS, consts.CUSTOM_TIME],
            print_value=True,
        )

        self.params.max_records = validator.validate_positive(
            "Max Records To Return", self.params.max_records
        )

        if self.params.time_frame == consts.CUSTOM_TIME:
            self._validate_dates()

    def _validate_dates(self):
        if self.params.start_time is None:
            raise CloudLoggingManagerError(
                'Missing value for parameter "Start Time" this value is mandatory'
                ' when "Custom" is selected for parameter "Time Frame".'
            )

        try:
            self.params.start_time = datetime.fromisoformat(
                self.params.start_time
            ).isoformat()
        except ValueError as error:
            raise CloudLoggingManagerError(
                f"Invalid iso format of start time: {self.params.start_time}"
            ) from error
        try:
            if self.params.end_time:
                self.params.end_time = datetime.fromisoformat(
                    self.params.end_time
                ).isoformat()
        except ValueError as error:
            raise CloudLoggingManagerError(
                f"Invalid iso format of end time: {self.params.end_time}"
            ) from error

    def _init_api_clients(self) -> CloudLoggingApiManager:
        auth_manager = build_auth_manager(self.soar_action)
        api_params = build_api_manager_params(auth_manager)

        return CloudLoggingApiManager(auth_manager.prepare_session(), api_params)

    def _perform_action(self, _: None) -> None:
        logs, final_query = self.api_client.execute_query(
            query=self.params.query,
            project_id=self.params.project_id,
            organization_id=self.params.organization_id,
            time_frame=self.params.time_frame,
            start_time=self.params.start_time,
            end_time=self.params.end_time,
            max_results=self.params.max_records,
        )

        message = (
            f'Successfully executed query "{final_query}" in Cloud Logging'
            if logs
            else "No results were found for the provided query."
        )
        self.logger.info(message)
        self.output_message = message
        self.json_results = logs
        if not logs:
            self.result_value = False


def main() -> None:
    ExecuteQuery().run()


if __name__ == "__main__":
    main()
