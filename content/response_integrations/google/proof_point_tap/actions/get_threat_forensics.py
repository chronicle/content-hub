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
from TIPCommon.transformation import convert_list_to_comma_string, string_to_multi_value
from TIPCommon.types import SingleJson
from TIPCommon.validation import ParameterValidator
from ..core import action_init
from ..core import constants
from ..core import datamodels
from ..core.exceptions import ThreatIdNotFoundError
from ..core.proof_point_tap_manager import proof_point_tap_manager


class GetThreatForensics(Action):
    def __init__(self) -> None:
        super().__init__(constants.GET_THREAT_FORENSICS)
        self.output_message: str = ""
        self.json_results: SingleJson = {}
        self.error_output_message: str = (
            f'Error executing action "{constants.GET_THREAT_FORENSICS}".'
        )
        self.successful_threat_ids: list[str] = []
        self.failed_threat_ids: list[str] = []
        self.invalid_threat_ids: list[str] = []

    def _extract_action_parameters(self) -> None:
        self.params.threat_id = extract_action_param(
            self.soar_action,
            param_name="Threat ID",
            print_value=True,
        )
        self.params.include_campaign_forensics = extract_action_param(
            self.soar_action,
            param_name="Include Campaign Forensics",
            default_value=False,
            input_type=bool,
            print_value=True,
        )
        self.params.max_results = extract_action_param(
            self.soar_action,
            param_name="Max Results To Return",
            is_mandatory=True,
            default_value=50,
            print_value=True,
            input_type=int,
        )
        self.params.threat_id = string_to_multi_value(
            string_value=self.params.threat_id, only_unique=True
        )

    def _validate_params(self) -> None:
        validator = ParameterValidator(siemplify=self.soar_action)
        validator.validate_range(
            param_name="Max Results To Return",
            value=self.params.max_results,
            min_limit=1,
            max_limit=constants.MAX_LIMIT,
        )

    def _init_api_clients(self) -> proof_point_tap_manager:
        return action_init.create_api_client(self.soar_action)

    def _perform_action(self, _) -> None:
        results = self._get_threat_forensics(threat_ids=self.params.threat_id)
        if self.successful_threat_ids:
            self.output_message = (
                "Successfully returned forensics for the following threats in "
                "Proofpoint TAP: "
                f"{convert_list_to_comma_string(self.successful_threat_ids)}"
            )
            self.json_results = _get_json_result(results)

        if self.failed_threat_ids:
            failure_message = (
                "No forensics were found for the following threats in Proofpoint TAP: "
                f"{convert_list_to_comma_string(self.failed_threat_ids)}"
            )
            if self.successful_threat_ids:
                self.output_message += f"\n{failure_message}"
            else:
                self.output_message = (
                    "No forensics were found for the provided threats in "
                    "Proofpoint TAP."
                )

    def _get_threat_forensics(
        self,
        threat_ids: list[str],
    ) -> list[datamodels.ThreatReport]:
        results = []
        for threat_id in threat_ids:
            try:
                reports = self.api_client.get_threat_forensics(
                    threat_id=threat_id,
                    include_campaign_forensics=self.params.include_campaign_forensics,
                    max_results=self.params.max_results,
                )
                if reports:
                    self.successful_threat_ids.append(threat_id)
                    results.extend(reports)
                else:
                    self.failed_threat_ids.append(threat_id)
            except ThreatIdNotFoundError as e:
                self.logger.error(
                    f"Failed to get forensics for threat ID {threat_id}: {e}"
                )
                self.logger.exception(e)
                self.invalid_threat_ids.append(threat_id)

        if self.invalid_threat_ids:
            raise ThreatIdNotFoundError(
                "the following threat IDs are invalid: "
                f"{convert_list_to_comma_string(self.invalid_threat_ids)}. "
                "Please check the spelling."
            )

        return results


def _get_json_result(results: list[datamodels.ThreatReport]) -> SingleJson:
    return [report.to_json() for report in results]


def main() -> NoReturn:
    GetThreatForensics().run()


if __name__ == "__main__":
    main()
