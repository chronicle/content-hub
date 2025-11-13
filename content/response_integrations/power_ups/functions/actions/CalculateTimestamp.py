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
from typing import TYPE_CHECKING

import arrow
from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.validation import ParameterValidator

from ..core.constants import (
    CALCULATE_TIMESTAMP_SCRIPT_NAME,
    DEFAULT_OUTPUT_EPOCH_FORMAT_INDICATOR,
    DEFAULT_TIMESTAMP_DELTA,
    TIMESTAMP_DELTA_REGEX,
    InputType,
)

if TYPE_CHECKING:
    from typing import Any, NoReturn

    from TIPCommon.types import SingleJson


class CalculateTimestampAction(Action):
    """Action to calculate timestamps based on various inputs and deltas."""

    def __init__(self) -> None:
        super().__init__(CALCULATE_TIMESTAMP_SCRIPT_NAME)
        self.output_message: str = (
            "Successfully calculated timestamps based on the provided parameters."
        )

    def _init_api_clients(self) -> None:
        """Initialize API clients if required (placeholder)."""

    def _extract_action_parameters(self) -> None:
        """Extracts all action parameters."""
        self.params.input_type = extract_action_param(
            self.soar_action,
            "Input Type",
            default_value=InputType.CURRENT_TIME.value,
            print_value=True,
        )
        self.params.custom_timestamp = extract_action_param(
            self.soar_action,
            "Custom Timestamp",
            print_value=True,
        )
        self.params.custom_timestamp_format = extract_action_param(
            self.soar_action,
            "Custom Timestamp Format",
            print_value=True,
        )
        self.params.timestamp_delta = extract_action_param(
            self.soar_action,
            "Timestamp Delta",
            default_value=DEFAULT_TIMESTAMP_DELTA,
            print_value=True,
        )
        self.params.output_timestamp_format = extract_action_param(
            self.soar_action,
            "Output Timestamp Format",
            default_value=DEFAULT_OUTPUT_EPOCH_FORMAT_INDICATOR,
            print_value=True,
        )

    def _validate_params(self) -> None:
        """Validates extracted parameters."""
        validator = ParameterValidator(self.soar_action)
        self.params.input_type = validator.validate_ddl(
            "Input Type",
            self.params.input_type,
            [it.value for it in InputType],
        )
        self.params.delta_strings = validator.validate_csv(
            "Timestamp Delta",
            self.params.timestamp_delta,
        )

        self._validate_custom_timestamp()
        self._validate_output_format(self.params.output_timestamp_format)

    def _validate_custom_timestamp(self) -> None:
        """Validates the custom timestamp when required."""
        if self.params.input_type != InputType.CUSTOM_TIMESTAMP.value:
            return

        if not self.params.custom_timestamp:
            raise ValueError(
                '“Custom Timestamp” parameter should have a value, '
                'if “Input Type” is set to “Custom Timestamp”.'
            )

        if self.params.custom_timestamp_format:
            try:
                datetime.datetime.strptime(
                    self.params.custom_timestamp,
                    self.params.custom_timestamp_format,
                )
            except ValueError as exc:
                raise ValueError(
                    'input provided in “Custom Timestamp” and “Custom Timestamp Format” '
                    'is not aligned. Please check the spelling.'
                ) from exc

    def _validate_output_format(self, fmt: str) -> None:
        """Ensures valid output timestamp format."""
        if (
            fmt
            and fmt != DEFAULT_OUTPUT_EPOCH_FORMAT_INDICATOR
            and not fmt.startswith("%")
        ):
            raise ValueError("Invalid 'Output Timestamp Format' provided")

    def _perform_action(self, _: Any = None) -> None:
        original_timestamp = self._get_original_timestamp()
        json_result = self._build_json_result(original_timestamp)

        invalid_deltas: list[str] = []
        for delta in self.params.delta_strings:
            result = self._calculate_shifted_timestamp(original_timestamp, delta)
            if result is None:
                invalid_deltas.append(delta)
                continue
            delta_key, shifted_value = result
            json_result["calculated_timestamps"][delta_key] = shifted_value

        if invalid_deltas:
            raise ValueError(
                "invalid values provided "
                f'in the “Timestamp Delta” parameter: {", ".join(invalid_deltas)}. '
                "Please check the spelling."
            )
        self.json_results: SingleJson = json_result

    def _get_original_timestamp(self) -> arrow.Arrow:
        """Returns the original timestamp based on input type."""
        match self.params.input_type:
            case InputType.CURRENT_TIME.value:
                return arrow.get()
            case InputType.ALERT_CREATION_TIME.value:
                alert_creation_ms = getattr(
                    self.soar_action.current_alert, "creation_time", None
                )
                if alert_creation_ms:
                    return arrow.get(alert_creation_ms / 1000)
                raise ValueError(
                    "Alert creation time not found in the current context."
                )
            case InputType.CASE_CREATION_TIME.value:
                case_creation_ms = getattr(self.soar_action.case, "creation_time", None)
                if case_creation_ms:
                    return arrow.get(case_creation_ms / 1000)
                raise ValueError("Case creation time not found in the current context.")
            case InputType.CUSTOM_TIMESTAMP.value:
                return self._parse_custom_timestamp(
                    self.params.custom_timestamp,
                    self.params.custom_timestamp_format,
                )
            case _:
                raise ValueError(f"Unsupported Input Type: {self.params.input_type}")

    def _parse_custom_timestamp(self, value: str, fmt: str | None) -> arrow.Arrow:
        """Parses custom timestamp string with or without format."""
        try:
            try:
                return arrow.get(value)

            except arrow.parser.ParserError:
                if fmt:
                    return arrow.get(value, fmt)
                num_value = int(value)
                return arrow.get(num_value / 1000 if len(value) == 13 else num_value)

        except Exception as exc:
            raise ValueError(
                'input provided in “Custom Timestamp” and “Custom Timestamp Format” '
                'is not aligned. Please check the spelling.'
            ) from exc

    def _build_json_result(self, original: arrow.Arrow) -> SingleJson:
        """Builds initial JSON result skeleton."""
        original_str = self._format_timestamp(
            original, self.params.output_timestamp_format
        )
        return {
            "original_timestamp": original_str,
            "calculated_timestamps": {},
        }

    def _calculate_shifted_timestamp(
        self,
        base_timestamp: arrow.Arrow,
        delta_str: str,
    ) -> tuple[str, Any] | None:
        """Calculates a shifted timestamp for a given delta string."""
        match = TIMESTAMP_DELTA_REGEX.match(delta_str)
        if not match:
            return None

        operator, value_str, unit_char = match.groups()
        value = int(value_str)
        if operator == "-":
            value = -value

        shift_kwargs = self._get_shift_kwargs(unit_char, value)
        if not shift_kwargs:
            return None

        shifted = base_timestamp.shift(**shift_kwargs)
        formatted_shifted = self._format_timestamp(
            shifted, self.params.output_timestamp_format
        )
        return f"timestamp{delta_str}", formatted_shifted

    def _format_timestamp(self, ts: arrow.Arrow, fmt: str) -> Any:
        """Formats timestamp based on output format."""
        if fmt == DEFAULT_OUTPUT_EPOCH_FORMAT_INDICATOR:
            return int(ts.timestamp)
        return ts.strftime(fmt)

    def _get_shift_kwargs(self, unit_char: str, value: int) -> dict[str, int]:
        """Maps a delta unit to arrow shift keyword."""
        unit_map = {
            "m": "months",
            "d": "days",
            "H": "hours",
            "M": "minutes",
            "S": "seconds",
        }
        key = unit_map.get(unit_char)
        return {key: value} if key else {}


def main() -> NoReturn:
    CalculateTimestampAction().run()


if __name__ == "__main__":
    main()
