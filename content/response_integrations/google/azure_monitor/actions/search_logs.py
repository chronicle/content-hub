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

from datetime import datetime, timezone
from dateutil.parser import parse as isoparse

from TIPCommon.extraction import extract_action_param
from TIPCommon.validation import ParameterValidator

from azure_monitor.core.base_action import BaseAction
from azure_monitor.core.constants import (
    DEFAULT_MIN_ROWS,
    DEFAULT_RESULTS_TO_RETURN,
    DEFAULT_TIME_FRAME,
    MAX_RESULTS_LIMIT,
    SEARCH_LOGS_SCRIPT_NAME,
    TimeFrameDDLEnum,
)
from azure_monitor.core.exceptions import AzureMonitorErrorInvalidParameterError

if TYPE_CHECKING:
    from typing import NoReturn

    from TIPCommon.types import SingleJson

    from azure_monitor.core.data_models import AzureLogEntry


SUCCESS_MESSAGE: str = (
    'Successfully returned results for the query "{query}" in Azure Monitor.'
)
NO_RESULTS_MESSAGE: str = (
    'No results were found for the query "{query}" in Azure Monitor.'
)


class SearchLogsAction(BaseAction):
    def __init__(self) -> None:
        super().__init__(SEARCH_LOGS_SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        self.params.workspace_id = extract_action_param(
            self.soar_action,
            param_name="Workspace ID",
            print_value=True,
        )
        self.params.query = extract_action_param(
            self.soar_action,
            param_name="Query",
            is_mandatory=True,
            print_value=True,
        )
        self.params.time_frame = extract_action_param(
            self.soar_action,
            param_name="Time Frame",
            default_value=DEFAULT_TIME_FRAME,
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
        self.params.max_results_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Results To Return",
            is_mandatory=True,
            input_type=int,
            default_value=DEFAULT_RESULTS_TO_RETURN,
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator: ParameterValidator = ParameterValidator(self.soar_action)
        self._validate_time_params(validator)
        self._validate_max_results_param(validator)

    def _validate_time_params(self, validator: ParameterValidator) -> None:
        """
        Validate the provided time_frame, start_time, end_time parameters
        & sets ISO8601 strings directly for API usage.

        Sets:
            self.params.start_time: str (ISO 8601)
            self.params.end_time: str (ISO 8601)
        """

        def _validate_iso8601(value: str, param_name: str) -> None:
            """Validate if given value is ISO 8601 datetime string."""
            try:
                isoparse(value)

            except (ValueError, TypeError) as error:
                raise AzureMonitorErrorInvalidParameterError(
                    f"'{param_name}' must be a valid ISO 8601 datetime string "
                    f"(e.g., '2025-10-29T10:15:00Z'). Provided: '{value}'"
                ) from error

        self.params.time_frame = validator.validate_ddl(
            param_name="Time Frame",
            value=self.params.time_frame,
            ddl_values=TimeFrameDDLEnum.values(),
            print_value=True,
        )
        time_frame = TimeFrameDDLEnum(self.params.time_frame)

        if time_frame != TimeFrameDDLEnum.CUSTOM:
            self.params.start_time = time_frame.to_start_time_iso()
            self.params.end_time = (
                datetime.now(timezone.utc)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z")
            )

            if self.params.start_time or self.params.end_time:
                self.logger.warn(
                    f"Time Frame is set to '{time_frame.value}'. Ignoring any "
                    "'Start Time' or 'End Time' parameters provided by the user."
                )

        else:
            if not self.params.start_time:
                raise AzureMonitorErrorInvalidParameterError(
                    "'Start Time' must be provided if 'Time Frame' is set to 'Custom'."
                )
            _validate_iso8601(self.params.start_time, "Start Time")

            if self.params.end_time:
                _validate_iso8601(self.params.end_time, "End Time")

            self.params.end_time = self.params.end_time or datetime.now(
                timezone.utc
            ).isoformat(timespec="milliseconds").replace("+00:00", "Z")

        self.logger.info(f"Using start_time {self.params.start_time}")
        self.logger.info(f"Using end_time {self.params.end_time}")

    def _validate_max_results_param(self, validator: ParameterValidator) -> None:
        self.params.max_results_to_return = validator.validate_range(
            param_name="Max Results To Return",
            value=self.params.max_results_to_return,
            min_limit=DEFAULT_MIN_ROWS,
            max_limit=MAX_RESULTS_LIMIT,
            print_value=True,
        )

    def _perform_action(self, _=None):
        search_logs: list[AzureLogEntry] = self.api_client.search_logs(
            query=self.params.query,
            start_time=self.params.start_time,
            end_time=self.params.end_time,
            max_rows=self.params.max_results_to_return,
            workspace_id=self.params.workspace_id,
        )
        if not search_logs:
            self.output_message = NO_RESULTS_MESSAGE.format(query=self.params.query)
            return

        self.output_message: str = SUCCESS_MESSAGE.format(query=self.params.query)
        self.json_results: list[SingleJson] = [
            search_log.to_json() for search_log in search_logs
        ]


def main() -> NoReturn:
    SearchLogsAction().run()


if __name__ == "__main__":
    main()
