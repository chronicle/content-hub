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
from ..core import constants

from ..core.base_action import BaseAction
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import construct_csv, dict_to_flat
from TIPCommon.validation import ParameterValidator

if TYPE_CHECKING:
    from typing import List, Never, NoReturn

    from TIPCommon.types import SingleJson


class SimpleOsSearch(BaseAction):
    def __init__(self) -> None:
        super().__init__(constants.SIMPLE_OS_SEARCH_SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        self.params.index = extract_action_param(
            self.soar_action,
            param_name="Index",
            print_value=True,
            is_mandatory=True,
        )
        self.params.query = extract_action_param(
            self.soar_action,
            param_name="Query",
            print_value=True,
            is_mandatory=True,
        )
        self.params.limit = extract_action_param(
            self.soar_action,
            param_name="Limit",
            print_value=True,
            is_mandatory=True,
        )

    def _validate_params(self) -> None:
        validator: ParameterValidator = ParameterValidator(self.soar_action)
        validator.validate_positive(param_name="Limit", value=self.params.limit)

    def _perform_action(self, _: Never) -> None:
        results, status, _ = self.api_client.simple_os_search(
            self.params.index, self.params.query, self.params.limit
        )
        if status:
            self.output_message: str = (f"Query ran successfully {len(results)} "
                                        "hits found")
        else:
            self.output_message: str = "ERROR: Query failed to run"

        if results:
            flat_results: List[SingleJson] = []
            for result in results:
                flat_result: SingleJson = dict_to_flat(result)
                flat_results.append(flat_result)

            csv_output: str = construct_csv(flat_results)
            self.soar_action.result.add_data_table(
                f"Results - Total {len(results)}", csv_output
            )
            self.soar_action.result.add_result_json(results)

        self.result_value: bool = True


def main() -> NoReturn:
    SimpleOsSearch().run()


if __name__ == "__main__":
    main()
