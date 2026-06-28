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
from extrahop.core import action_init
from extrahop.core import constants

from extrahop.core.ExtrahopExceptions import InvalidDetectionIDError, InvalidParameterError
from extrahop.core.ExtrahopManager import ExtrahopManager


class UpdateDetection(Action):

    def __init__(self) -> None:
        super().__init__(constants.UPDATE_DETECTION_SCRIPT_NAME)
        self.output_message: str = ""
        self.result_value: bool = False
        self.json_results: SingleJson = {}
        self.error_output_message: str = (
            f'Error executing action "{constants.UPDATE_DETECTION_SCRIPT_NAME}".'
        )

    def _extract_action_parameters(self) -> None:
        self.params.detection_id: str = extract_action_param(
            self.soar_action,
            param_name="Detection ID",
            is_mandatory=True,
            print_value=True,
        )
        self.params.status: str = extract_action_param(
            self.soar_action,
            param_name="Status",
            default_value=constants.DEFAULT_PARAM_VALUE,
            print_value=True,
        )
        self.params.resolution: str = extract_action_param(
            self.soar_action,
            param_name="Resolution",
            default_value=constants.DEFAULT_PARAM_VALUE,
            print_value=True,
        )
        self.params.assigned_to: str = extract_action_param(
            self.soar_action,
            param_name="Assign To",
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator = ParameterValidator(siemplify=self.soar_action)
        validator.validate_ddl(
            param_name="Status",
            value=self.params.status,
            ddl_values=constants.POSSIBLE_STATUS_VALUES,
            default_value=constants.DEFAULT_PARAM_VALUE,
            print_error=True,
        )
        validator.validate_ddl(
            param_name="Resolution",
            value=self.params.resolution,
            ddl_values=constants.POSSIBLE_RESOLUTION_VALUES,
            default_value=constants.DEFAULT_PARAM_VALUE,
            print_error=True,
        )
        if (
            self.params.status == constants.DEFAULT_PARAM_VALUE
            and not self.params.assigned_to
        ):
            raise InvalidParameterError(
                'Either "Status" or "Assign To" parameters '
                "should have a value.\n"
                "Possible values of \"Status\": "
                f"{', '.join(constants.STATUS_MAPPING.keys())}"
            )
        if self.params.status != constants.DEFAULT_PARAM_VALUE:
            if (
                constants.STATUS_MAPPING[self.params.status]
                == constants.CLOSED_STATUS.lower()
                and self.params.resolution == constants.DEFAULT_PARAM_VALUE
            ):
                raise InvalidParameterError(
                    f"Resolution is required when status is {constants.CLOSED_STATUS}."
                )

        if (
            self.params.status != constants.CLOSED_STATUS
            and self.params.resolution != constants.DEFAULT_PARAM_VALUE
        ):
            raise InvalidParameterError(
                "Resolution should not be provided unless the status "
                f"is {constants.CLOSED_STATUS}."
            )

    def _init_api_clients(self) -> ExtrahopManager:
        return action_init.create_api_client(self.soar_action)

    def _perform_action(self, _) -> None:
        try:
            results = self.api_client.update_detection(
                detection_id=self.params.detection_id,
                status=self.params.status,
                assign_to=self.params.assigned_to,
                resolution=self.params.resolution,
            )
            self.result_value = True
            self.json_results = results.to_json()
            self.output_message = (
                "Successfully updated detection with ID "
                f"{self.params.detection_id} in {constants.INTEGRATION_NAME}."
            )

        except InvalidDetectionIDError as e:
            raise InvalidDetectionIDError(
                f"Detection with ID \"{self.params.detection_id}\" wasn't found in "
                f"{constants.INTEGRATION_NAME}. Please check the spelling."
            ) from e


def main() -> NoReturn:
    UpdateDetection().run()


if __name__ == "__main__":
    main()
