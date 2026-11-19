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
from typing import NoReturn

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.types import SingleJson
from TIPCommon.validation import ParameterValidator
from ..core import action_init
from ..core import constants
from ..core import datamodels
from ..core.exceptions import InvalidParameterError, ProofPointTapNotFoundError
from ..core.ProofPointTapManager import ProofPointTapManager


class ListCampaigns(Action):
    def __init__(self) -> None:
        super().__init__(constants.LIST_CAMPAIGNS_SCRIPT_NAME)
        self.output_message: str = (
            "Successfully returned campaigns from Proofpoint TAP."
        )
        self.json_results: SingleJson = {}
        self.error_output_message: str = (
            f'Error executing action "{constants.LIST_CAMPAIGNS_SCRIPT_NAME}".'
        )

    def _extract_action_parameters(self) -> None:
        self.params.time_frame: str = extract_action_param(
            self.soar_action,
            param_name="Time Frame",
            default_value=constants.POSSIBLE_TIMEFRAME_TO_HOURS_VALUES[0],
            print_value=True,
        )
        self.params.start_time: str = extract_action_param(
            self.soar_action,
            param_name="Start Time",
            print_value=True,
        )
        self.params.end_time: str = extract_action_param(
            self.soar_action,
            param_name="End Time",
            print_value=True,
        )
        self.params.max_results: int = extract_action_param(
            self.soar_action,
            param_name="Max Results To Return",
            is_mandatory=True,
            default_value=50,
            print_value=True,
            input_type=int,
        )

    def _validate_params(self) -> None:
        validator = ParameterValidator(siemplify=self.soar_action)
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
        if self.params.time_frame == "Custom" and not self.params.start_time:
            raise InvalidParameterError("Start Time is required for custom time frame.")

        if self.params.time_frame != "Custom" and self.params.start_time:
            raise InvalidParameterError('Please select "Custom"  in "Time Frame"')

    def _init_api_clients(self) -> ProofPointTapManager:
        return action_init.create_api_client(self.soar_action)

    def _perform_action(self, _) -> None:
        try:
            results = self.api_client.list_campaigns(
                time_frame=self.params.time_frame,
                max_results=self.params.max_results,
                custom_start=self.params.start_time,
                custom_end=self.params.end_time,
            )

            if not results:
                self.output_message = (
                    "No campaigns were found in Proofpoint TAP "
                    "for the provided criteria."
                )

            self.json_results = _get_json_result(results)

        except ProofPointTapNotFoundError as e:
            self.logger.error(
                "No campaigns were found in Proofpoint TAP for the provided criteria."
            )
            self.logger.exception(e)
            self.output_message = (
                "No campaigns were found in Proofpoint TAP for the provided criteria."
            )


def _get_json_result(results: list[datamodels.Campaign]) -> SingleJson:
    return {"campaigns": [campaign.to_json() for campaign in results]}


def main() -> NoReturn:
    ListCampaigns().run()


if __name__ == "__main__":
    main()
