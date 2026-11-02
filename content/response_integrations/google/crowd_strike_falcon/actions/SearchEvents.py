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

from dataclasses import dataclass, asdict
import json
from typing import NoReturn

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyLogger import SiemplifyLogger
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.extraction import extract_action_param
from TIPCommon.types import SingleJson
from TIPCommon.validation import ParameterValidator

from crowd_strike_falcon.core.AsyncActionBaseClass import ActionResult, AsyncActionBaseClass
from crowd_strike_falcon.core import constants
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager
from crowd_strike_falcon.core.CrowdStrikeParser import CrowdStrikeParser
from crowd_strike_falcon.core.exceptions import CrowdStrikeManagerError, ExpiredJobIdError, InvalidParameterError


@dataclass
class ActionData:
    job_id: str
    status: str

    @classmethod
    def from_json(cls, action_data: dict) -> ActionData:
        return cls(action_data.get("job_id"), action_data.get("status"))


@dataclass
class ActionMessages:
    data: ActionData
    logger: SiemplifyLogger
    _json_results: SingleJson = None

    def log_messages(self) -> None:
        self.logger.info(f"Search job ID {self.data.job_id} created successfully.")
        self.logger.info(f"Job ID status: {self.data.status}")

    def timeout_msg(self) -> str:
        return "Action failed to Search Events until timeout."

    def success_msg(self, query: str) -> str:
        if not self.json_results["events"]:
            return self._no_events_msg(query=query)

        return (
            f'Successfully returned results for the query "{query}" in '
            f"{constants.INTEGRATION_NAME}."
        )

    def _no_events_msg(self, query: str) -> str:
        return (
            f'No results were found for the query "{query}" in '
            f"{constants.INTEGRATION_NAME}."
        )

    def failed_msg(self) -> str:
        return "Search job did not return any results or failed to complete."

    def in_progress_msg(self) -> str:
        return "Waiting for the search job to finish ..."

    @property
    def json_results(self) -> SingleJson:
        return self._json_results

    @json_results.setter
    def json_results(self, value: SingleJson) -> None:
        self._json_results = value


class SearchEvents(AsyncActionBaseClass):
    def __init__(self, siemplify) -> None:
        super().__init__(siemplify)
        self.parser = CrowdStrikeParser()
        self.results = ActionData(job_id="", status="")
        self.action_msg = ActionMessages(data=self.results, logger=self.logger)

    def _extract_action_configuration(self):
        self.params.repository: str = extract_action_param(
            siemplify=self.siemplify,
            param_name="Repository",
            default_value=constants.DEFAULT_REPOSITORY_TO_SEARCH,
            is_mandatory=True,
            print_value=True,
        )
        self.params.query: str = extract_action_param(
            siemplify=self.siemplify,
            param_name="Query",
            is_mandatory=True,
            print_value=True,
        )
        self.params.time_frame: str = extract_action_param(
            siemplify=self.siemplify,
            param_name="Time Frame",
            default_value=constants.DEFAULT_TIME_FRAME,
            print_value=True,
        )
        self.params.start_time: str = extract_action_param(
            siemplify=self.siemplify,
            param_name="Start Time",
            print_value=True,
        )
        self.params.end_time: str = extract_action_param(
            siemplify=self.siemplify,
            param_name="End Time",
            print_value=True,
        )
        self.params.max_results: int = extract_action_param(
            siemplify=self.siemplify,
            param_name="Max Results To Return",
            default_value=constants.SEARCH_EVENTS_DEFAULT_LIMIT,
            input_type=int,
            print_value=True,
        )
        self.params.additional_data: dict = extract_action_param(
            siemplify=self.siemplify,
            param_name="additional_data",
            default_value="{}",
        )

    def _validate_params(self, validator: ParameterValidator) -> None:
        validator.validate_ddl(
            param_name="Repository",
            value=self.params.repository,
            ddl_values=constants.POSSIBLE_REPOSITORY_VALUES,
        )
        validator.validate_ddl(
            param_name="Time Frame",
            value=self.params.time_frame,
            ddl_values=constants.POSSIBLE_TIMEFRAME_VALUES,
        )
        validator.validate_range(
            param_name="Max Results To Return",
            value=self.params.max_results,
            min_limit=1,
            max_limit=constants.SEARCH_EVENTS_MAX_LIMIT,
        )
        self.params.additional_data = validator.validate_json(
            param_name="additional_data",
            json_string=self.params.additional_data,
            default_value="{}",
            print_value=False,
        )
        if self.params.time_frame == constants.TIME_FRAME_CUSTOM:
            if not self.params.start_time:
                raise InvalidParameterError(
                    "Start Time is required for custom time frame."
                )

        if (
            self.params.time_frame != constants.TIME_FRAME_CUSTOM
            and self.params.start_time
        ):
            raise InvalidParameterError(
                f'Please select "{constants.TIME_FRAME_CUSTOM}" in "Time Frame"'
            )

    def _perform_action(self, manager: CrowdStrikeManager):
        self._set_action_data()
        self._create_search_job(manager)
        job_results = self._get_search_job_results(manager)
        self._set_action_result(job_results)
        self._set_json_results(job_results)
        self._log_messages()

        return self._finalize_action()

    def _create_search_job(self, manager: CrowdStrikeManager) -> None:
        if not self.results.job_id:
            job_id = manager.initiate_search_job(
                repository=self.params.repository,
                query=self.params.query,
                time_frame=self.params.time_frame,
                max_results=self.params.max_results,
                start_time=self.params.start_time,
                end_time=self.params.end_time,
            )
            self.results.job_id = job_id

    def _get_search_job_results(self, manager: CrowdStrikeManager) -> SearchEvents:
        try:
            job_results = manager.get_search_job_results(
                job_id=self.results.job_id,
                repository=self.params.repository,
            )
        except CrowdStrikeManagerError as e:
            raise ExpiredJobIdError(
                f'query Job "{self.results.job_id}" has expired. '
                "Please decrease the async polling interval."
            ) from e

        return job_results

    def _set_action_result(self, job_results: SearchEvents) -> None:
        self.results.job_id = job_results.job_id
        self.results.status = job_results.status

    def _set_json_results(self, job_results: SearchEvents) -> None:
        if self.results.status == constants.EventStatus.COMPLETED.value:
            json_data = {"events": job_results.events}
            self.action_msg.json_results = json_data
            self.siemplify.result.add_result_json(json_data)

    def _finalize_action(self) -> ActionResult:
        if self._is_timeout():
            return self._finalize_action_on_timeout()

        if self.results.status == constants.EventStatus.IN_PROGRESS.value:
            return self._finalize_action_on_inprogress()

        if self.results.status != constants.EventStatus.COMPLETED.value:
            return self._finalize_action_on_failure()

        return self._finalize_action_on_success()

    def _set_action_data(self) -> None:
        if self.params.additional_data:
            self.results = ActionData.from_json(self.params.additional_data)
            self.action_msg = ActionMessages(data=self.results, logger=self.logger)

    def _finalize_action_on_inprogress(self) -> ActionResult:
        self.output_messages.append(self.action_msg.in_progress_msg())
        return ActionResult(
            status=ExecutionState.IN_PROGRESS,
            result_value=json.dumps(asdict(self.results)),
        )

    def _finalize_action_on_success(self) -> ActionResult:
        self.output_messages.append(
            self.action_msg.success_msg(query=self.params.query)
        )
        return ActionResult(
            status=ExecutionState.COMPLETED,
            result_value=True,
        )

    def _finalize_action_on_failure(self) -> ActionResult:
        self.output_messages.append(self.action_msg.failed_msg)
        return ActionResult(
            status=ExecutionState.FAILED,
            result_value=False,
        )

    def _finalize_action_on_timeout(self) -> ActionResult:
        self.output_messages.append(self.action_msg.timeout_msg())
        return ActionResult(
            status=ExecutionState.TIMED_OUT,
            result_value=True,
        )

    def _log_messages(self) -> None:
        self.action_msg.log_messages()


@output_handler
def main() -> NoReturn:
    chronicle_soar = SiemplifyAction()
    chronicle_soar.script_name = constants.SEARCH_EVENTS_SCRIPT_NAME
    action = SearchEvents(chronicle_soar)
    action.run()


if __name__ == "__main__":
    main()
