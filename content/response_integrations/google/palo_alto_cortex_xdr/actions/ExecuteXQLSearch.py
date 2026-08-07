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

import datetime as dt
import json
import sys
from typing import TYPE_CHECKING

from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time
from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.extraction import extract_action_param
from TIPCommon.smp_time import is_approaching_action_timeout
from TIPCommon.utils import is_first_run
from TIPCommon.validation import ParameterValidator
from ..core import action_init
from ..core.base_action import BaseAction
from ..core import constants
from ..core import datamodels
from ..core.exceptions import PaloAltoXdrValidationError
from ..core.XDRManager import SearchXQLParameters

if TYPE_CHECKING:
    from typing import NoReturn

    from TIPCommon.types import SingleJson

    from ..core.XDRManager import XDRManager


SUCCESS_MESSAGE: str = (
    'Successfully returned results for the query "{query}" in '
    f"{constants.VENDOR} {constants.PRODUCT}."
)
INPROGRESS_MESSAGE: str = "Waiting for the search job to finish…"
TIMEOUT_ERROR_MESSAGE: str = (
    "Action ran into a timeout during execution. Please increase the timeout in IDE."
)


class ExecuteXQLSearch(BaseAction):
    def __init__(self) -> None:
        super().__init__(constants.EXECUTE_XQL_SEARCH_ACTION_SCRIPT_NAME)
        self.error_output_message: str = (
            "Error executing action "
            f'"{constants.EXECUTE_XQL_SEARCH_ACTION_SCRIPT_NAME}".'
        )

    def _extract_action_parameters(self) -> None:
        self.params.query = extract_action_param(
            self.soar_action,
            param_name="Query",
            print_value=True,
        )
        self.params.time_frame = extract_action_param(
            self.soar_action,
            param_name="Time Frame",
            default_value=constants.POSSIBLE_TIMEFRAME_TO_HOURS_VALUES[0],
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
        self.params.max_results = extract_action_param(
            self.soar_action,
            param_name="Max Results To Return",
            is_mandatory=True,
            default_value=constants.XQL_DEFAULT_LIMIT,
            print_value=True,
            input_type=int,
        )
        self.params.additional_data = json.loads(
            extract_action_param(
                self.soar_action,
                param_name="additional_data",
                default_value="{}",
                print_value=True,
            )
        )

    def _validate_params(self) -> None:
        validator: ParameterValidator = ParameterValidator(siemplify=self.soar_action)
        validator.validate_ddl(
            param_name="Time Frame",
            value=self.params.time_frame,
            ddl_values=constants.POSSIBLE_TIMEFRAME_TO_HOURS_VALUES,
        )
        validator.validate_range(
            param_name="Max Results To Return",
            value=self.params.max_results,
            min_limit=1,
            max_limit=constants.MAX_LIMIT,
        )
        self._validate_time_params(validator=validator)

    def _validate_time_params(self, validator: ParameterValidator) -> None:
        """Validate the provided time_frame, start_time, end_time parameters
        & Sets `epoch time in ms` parameters based on them.

        Sets:
            self.params.start_time: `epoch time in ms`
            self.params.end_time: `epoch time in ms`
        """
        current_time: int = convert_datetime_to_unix_time(dt.datetime.now())
        if (
            self.params.time_frame == constants.TimeFrameDDLEnum.CUSTOM.value
            and not self.params.start_time
        ):
            raise PaloAltoXdrValidationError(
                "Start Time is required for custom time frame."
            )

        self.params.time_frame = validator.validate_ddl(
            param_name="Time Frame",
            value=self.params.time_frame,
            ddl_values=constants.TimeFrameDDLEnum.values(),
            print_value=True,
        )
        time_frame = constants.TimeFrameDDLEnum(self.params.time_frame)
        if time_frame != constants.TimeFrameDDLEnum.CUSTOM:
            self.params.start_time = convert_datetime_to_unix_time(
                dt=time_frame.to_start_date()
            )
            self.params.end_time = current_time

        else:
            start_time = dt.datetime.fromisoformat(
                self.params.start_time.replace("Z", "+00:00"),
            )
            self.params.start_time = convert_datetime_to_unix_time(start_time)
            self.params.end_time = (
            convert_datetime_to_unix_time(
                dt.datetime.fromisoformat(
                    self.params.end_time.replace("Z", "+00:00")
                )
            )
            if self.params.end_time is not None
            else current_time
            )

        self.logger.info(f"Using start_time {repr(self.params.start_time)}")
        self.logger.info(f"Using end_time {repr(self.params.end_time)}")

    def _init_api_clients(self) -> XDRManager:
        return action_init.create_api_client(self.soar_action)

    def _perform_action(self, _) -> None:
        search_params: SearchXQLParameters = SearchXQLParameters(
            query=self.params.query,
            start_time=self.params.start_time,
            end_time=self.params.end_time,
            limit=self.params.max_results,
        )
        query_id: str = self._get_xql_query_id(search_params)
        query_result: datamodels.XQLSearchResult = self._get_xql_search_result(query_id)
        self._set_action_results(query_id, query_result)

    def _execute_xql_search(
        self,
        search_params: SearchXQLParameters,
    ) -> list[datamodels.XQLSearch]:
        return self.api_client.execute_xql_search(search_params)

    def _get_xql_search_result(self, query_id: str) -> datamodels.XQLSearchResult:
        return self.api_client.get_xql_search_results(query_id=query_id)

    def _get_xql_query_id(
        self,
        search_params: SearchXQLParameters,
    ) -> str:
        if is_first_run(sys.argv):
            result = self._execute_xql_search(search_params)
            return result.query_id

        return self.params.additional_data.get("query_id")

    def _set_action_results(
        self,
        query_id: str,
        xql_result: datamodels.XQLSearchResult,
    ) -> None:
        if self._is_approaching_async_timeout():
            self._set_action_timeout()
            return
        if xql_result.status == constants.XQL_PENDING:
            self._set_action_inprogress(query_id)
        else:
            self._set_action_on_success(xql_result)

    def _set_action_inprogress(self, query_id: str) -> None:
        self.result_value = json.dumps({"query_id": query_id})
        self.output_message = INPROGRESS_MESSAGE
        self.execution_state = ExecutionState.IN_PROGRESS

    def _set_action_on_success(self, xql_result: datamodels.XQLSearchResult) -> None:
        if not xql_result.events:
            self.output_message = (
                f'No results were found for the query "{self.params.query}" '
                f"in {constants.VENDOR} {constants.PRODUCT}."
            )

        else:
            self.output_message = SUCCESS_MESSAGE.format(query=self.params.query)
            self.json_results = {
                "events": [event.to_json() for event in xql_result.events]
            }

    def _set_action_timeout(self) -> None:
        self.output_message = TIMEOUT_ERROR_MESSAGE
        self.execution_state = ExecutionState.TIMED_OUT

    def _is_approaching_async_timeout(self) -> bool:
        """Determine whether the action approaches asynchronous timeout."""
        return is_approaching_action_timeout(
            self.soar_action.async_total_duration_deadline,
        )


def main() -> NoReturn:
    ExecuteXQLSearch().run()


if __name__ == "__main__":
    main()
