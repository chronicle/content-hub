# Copyright 2025 Google LLC
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

import datetime
import re
from typing import TYPE_CHECKING

import arrow
from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.validation import ParameterValidator

if TYPE_CHECKING:
    from typing import NoReturn
    
    from TIPCommon.types import SingleJson

SCRIPT_NAME = "Calculate Timestamp"
INPUT_TYPE_CURRENT_TIME = "Current Time"
INPUT_TYPE_ALERT_CREATION_TIME = "Alert Creation Time"
INPUT_TYPE_CASE_CREATION_TIME = "Case Creation Time"
INPUT_TYPE_CUSTOM_TIMESTAMP = "Custom Timestamp"
INPUT_TYPE_OPTIONS = [
    INPUT_TYPE_CURRENT_TIME,
    INPUT_TYPE_ALERT_CREATION_TIME,
    INPUT_TYPE_CASE_CREATION_TIME,
    INPUT_TYPE_CUSTOM_TIMESTAMP,
]
DEFAULT_TIMESTAMP_DELTA = "+30M,-30M"

TIMESTAMP_DELTA_REGEX = re.compile(r"^([+-])(\d+)([mdHMS])$")

DEFAULT_OUTPUT_EPOCH_FORMAT_INDICATOR = "epoch"


class CalculateTimestampAction(Action):
    """
    Action to calculate timestamps based on various inputs and deltas.
    """

    def __init__(self) -> None:
        super().__init__(SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        """
        Extracts and validates action parameters.
        """
        self.params.input_type = extract_action_param(
            self.soar_action,
            "Input Type",
            default_value=INPUT_TYPE_CURRENT_TIME,
            print_value=True,
        )
        self.params.custom_timestamp_str = extract_action_param(
            self.soar_action,
            "Custom Timestamp",
            print_value=True,
        )
        self.params.custom_timestamp_format = extract_action_param(
            self.soar_action,
            "Custom Timestamp Format",
            print_value=True,
        )
        self.params.timestamp_delta_csv = extract_action_param(
            self.soar_action, "Timestamp Delta",
            default_value=DEFAULT_TIMESTAMP_DELTA,
            print_value=True,
        )
        self.params.output_timestamp_format = extract_action_param(
            self.soar_action, "Output Timestamp Format",
            default_value=DEFAULT_OUTPUT_EPOCH_FORMAT_INDICATOR,
            print_value=True,
        )

    def _validate_params(self) -> None:
        """
        Validates the extracted parameters.
        """
        validator = ParameterValidator(self.soar_action)
        self.params.input_type = validator.validate_ddl(
            "Input Type", self.params.input_type, INPUT_TYPE_OPTIONS
        )
        self.params.delta_strings = validator.validate_csv(
            "Timestamp Delta",
            self.params.timestamp_delta_csv)

        if (self.params.input_type == INPUT_TYPE_CUSTOM_TIMESTAMP 
           and not self.params.custom_timestamp_str):
            raise ValueError(
                "\"Custom Timestamp\" parameter should have a value, "
                "if \"Input Type\" is set to \"Custom Timestamp\". "
                "Please check the spelling"
            )

        if (self.params.input_type == INPUT_TYPE_CUSTOM_TIMESTAMP and
            self.params.custom_timestamp_format
            and self.params.custom_timestamp_str
            ):
            try:
                datetime.datetime.strptime(
                    self.params.custom_timestamp_str,
                    self.params.custom_timestamp_format)
            except ValueError:
                raise ValueError(
                    "input provided in \"Custom Timestamp\" and "
                    "\"Custom Timestamp format\" is not aligned. "
                    "Please check the spelling."
                )

        if (
            self.params.output_timestamp_format
            and 
            self.params.output_timestamp_format != DEFAULT_OUTPUT_EPOCH_FORMAT_INDICATOR
        ):
            if self.params.output_timestamp_format[0] != "%":
                raise ValueError("Invalid 'Output Timestamp Format' provided")
    
    def _init_api_clients(self) -> None:
        """Initialize API clients if required (placeholder)."""

    def _perform_action(self, _=None) -> None:
        """
        Main execution logic for the action.
        """
        calculated_timestamps_dict: SingleJson = {}
        json_result: SingleJson = {
            "original_timestamp": "",
            "calculated_timestamps": calculated_timestamps_dict,
        }

        original_timestamp_obj = self._get_original_timestamp(
            self.params.input_type,
            self.params.custom_timestamp_str,
            self.params.custom_timestamp_format,
        )

        if self.params.input_type == INPUT_TYPE_CUSTOM_TIMESTAMP:
            json_result["original_timestamp"] = self.params.custom_timestamp_str
        elif (
            self.params.output_timestamp_format
            == DEFAULT_OUTPUT_EPOCH_FORMAT_INDICATOR
        ):
            json_result["original_timestamp"] = int(original_timestamp_obj.timestamp)
        else:
            json_result["original_timestamp"] = original_timestamp_obj.strftime(
                self.params.output_timestamp_format
            )

        invalid_deltas: list[str] = []

        for delta_str in self.params.delta_strings:
            match = TIMESTAMP_DELTA_REGEX.match(delta_str)
            if not match:
                invalid_deltas.append(delta_str)
                continue

            operator, value_str, unit_char = match.groups()
            value: int = int(value_str)

            if operator == "-":
                value = -value

            shift_kwargs = self._get_shift_kwargs(unit_char, value)
            if not shift_kwargs:
                invalid_deltas.append(delta_str)
                continue

            shifted_timestamp_obj = original_timestamp_obj.shift(**shift_kwargs)

            if (
                self.params.output_timestamp_format
                == DEFAULT_OUTPUT_EPOCH_FORMAT_INDICATOR
            ):
                formatted_shifted_timestamp = int(shifted_timestamp_obj.timestamp)
            else:
                formatted_shifted_timestamp = shifted_timestamp_obj.strftime(
                    self.params.output_timestamp_format
                )

            calculated_timestamps_dict[f"timestamp{delta_str}"] = (
                formatted_shifted_timestamp
            )

        if invalid_deltas:
            raise ValueError(
                "Invalid values provided in the \"Timestamp Delta\". "
                "Please check the spelling."
            )
        message = "Successfully calculated timestamps based on the provided parameters."
        self.output_message = message
        self.result_value = True
        self.json_results = json_result

    def _get_original_timestamp(
        self, input_type: str,
        custom_timestamp_str: str,
        custom_timestamp_format: str) -> arrow.Arrow:
        if input_type == INPUT_TYPE_CURRENT_TIME:
            return arrow.get()
        if input_type == INPUT_TYPE_ALERT_CREATION_TIME:
            alert_creation_ms = getattr(
                self.soar_action.current_alert,
                "creation_time",
                None)
            if alert_creation_ms:
                return arrow.get(alert_creation_ms / 1000)
            raise ValueError("Alert creation time not found in the current context.")
        if input_type == INPUT_TYPE_CASE_CREATION_TIME:
            case_creation_ms = getattr(self.soar_action.case, "creation_time", None)
            if case_creation_ms:
                return arrow.get(case_creation_ms / 1000)
            raise ValueError("Case creation time not found in the current context.")
        if input_type == INPUT_TYPE_CUSTOM_TIMESTAMP:
            try:
                try:
                    return arrow.get(custom_timestamp_str)
                except arrow.parser.ParserError:
                    if custom_timestamp_format:
                        return arrow.get(custom_timestamp_str, custom_timestamp_format)
                    num_timestamp = int(custom_timestamp_str)
                    return arrow.get(
                        num_timestamp / 1000 if 
                        len(custom_timestamp_str) == 13 else num_timestamp)
            except Exception as e:
                raise ValueError(
                    "input provided in \"Custom Timestamp\" and "
                    "\"Custom Timestamp format\" is not aligned. "
                    f"Please check the spelling. {e}"
                )
        raise ValueError(f"Unsupported Input Type: {input_type}")

    def _get_shift_kwargs(self, unit_char: str, value: int) -> SingleJson:
        shift_map = {
            "m": "months",
            "d": "days",
            "H": "hours",
            "M": "minutes",
            "S": "seconds",
        }
        key = shift_map.get(unit_char)
        return {key: value} if key else {}


def main() -> NoReturn:
    CalculateTimestampAction().run()


if __name__ == "__main__":
    main()