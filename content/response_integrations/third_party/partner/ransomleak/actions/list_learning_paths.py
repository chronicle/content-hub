# Copyright 2026 RansomLeak
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

from TIPCommon.base.action import DataTable
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import construct_csv

from ..core.base_action import BaseAction
from ..core.constants import (
    DEFAULT_MAX_RESULTS,
    LIST_LEARNING_PATHS_ACTION_NAME,
    LIST_LEARNING_PATHS_SCRIPT_NAME,
)
from ..core.exceptions import RansomLeakValidationError


class ListLearningPathsAction(BaseAction):
    """List published RansomLeak learning paths, optionally filtered by name."""

    def __init__(self) -> None:
        super().__init__(LIST_LEARNING_PATHS_SCRIPT_NAME, LIST_LEARNING_PATHS_ACTION_NAME)

    def _extract_action_parameters(self) -> None:
        name_filter: str | None = extract_action_param(
            self.soar_action,
            param_name="Filter Value",
            print_value=True,
        )
        max_results: int | None = extract_action_param(
            self.soar_action,
            param_name="Max Results To Return",
            default_value=DEFAULT_MAX_RESULTS,
            input_type=int,
            print_value=True,
        )
        self.params.name_filter = (name_filter or "").strip().lower()
        self.params.max_results = max_results

    def _validate_params(self) -> None:
        if self.params.max_results is None or self.params.max_results < 1:
            msg = "'Max Results To Return' must be a positive number."
            raise RansomLeakValidationError(msg)

    def _perform_action(self, _: object = None) -> None:
        needle: str = self.params.name_filter
        paths = [
            path.to_json()
            for path in self.api_client.list_learning_paths()
            if not needle or needle in (path.name or "").lower()
        ][: self.params.max_results]

        if not paths:
            self.output_message = "No learning paths were found in RansomLeak for the provided criteria."
            self.result_value = False
            return
        self.json_results = paths
        self.data_tables.append(
            DataTable(
                data_table=construct_csv([
                    {"ID": p["id"], "Name": p["name"], "Description": p["description"] or ""} for p in paths
                ]),
                title="RansomLeak Learning Paths",
            ),
        )
        self.output_message = f"Successfully found {len(paths)} learning path(s) in RansomLeak."
        self.result_value = True


def main() -> NoReturn:
    ListLearningPathsAction().run()


if __name__ == "__main__":
    main()
