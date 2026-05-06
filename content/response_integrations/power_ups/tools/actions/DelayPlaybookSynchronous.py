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

import time
from datetime import UTC, datetime, timedelta
from typing import NoReturn

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.utils import is_empty_string_or_none
from TIPCommon.validation import ParameterValidator

from ..core.constants import (
    DELAY_PLAYBOOK_SYNCHRONOUS_SCRIPT_NAME,
    MAX_SYNC_DELAY_TIME_IN_SECONDS,
    MIN_SYNC_DELAY_TIME_IN_SECONDS,
)


class DelayPlaybookSyncAction(Action):
    def __init__(self) -> None:
        super().__init__(DELAY_PLAYBOOK_SYNCHRONOUS_SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        self.params.seconds = extract_action_param(
            self.soar_action,
            param_name="Seconds",
            is_mandatory=True,
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_action)
        if not is_empty_string_or_none(self.params.seconds):
            self.params.seconds = validator.validate_positive(
                param_name="Seconds",
                value=self.params.seconds,
            )
        self.params.seconds = validator.validate_range(
            param_name="Seconds",
            value=self.params.seconds,
            min_limit=MIN_SYNC_DELAY_TIME_IN_SECONDS,
            max_limit=MAX_SYNC_DELAY_TIME_IN_SECONDS,
        )

    def _init_api_clients(self) -> None:
        pass

    def _perform_action(self, _) -> None:
        target_date: datetime = datetime.now(UTC) + timedelta(
            seconds=self.params.seconds,
        )
        while (remaining_time := (target_date - datetime.now(UTC)).total_seconds()) >= 0:
            time.sleep(min(1, int(remaining_time)))

        self.output_message = (
            f"Reached the configured delay of {self.params.seconds} seconds at {target_date.isoformat()}"
        )


def main() -> NoReturn:
    DelayPlaybookSyncAction().run()


if __name__ == "__main__":
    main()
