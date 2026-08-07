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

from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import construct_csv
from TIPCommon.validation import ParameterValidator
from ..core import constants
from ..core.base_action import BaseAction

if TYPE_CHECKING:
    from typing import List, Never, NoReturn

    from TIPCommon.types import SingleJson


class DslSearch(BaseAction):
    def __init__(self) -> None:
        super().__init__(constants.DSL_SEARCH_SCRIPT_NAME)

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
            input_type=int,
        )

    def _validate_params(self) -> None:
        validator: ParameterValidator = ParameterValidator(self.soar_action)
        validator.validate_positive(param_name="Limit", value=self.params.limit)

    def _perform_action(self, _: Never) -> None:
        dsl_search_results, _ = self.api_client.dsl_search(
            self.soar_action,
            indices=self.params.index,
            query=self.params.query,
            max_results=self.params.limit,
        )

        if dsl_search_results:
            self.output_message: str = (
                f"Successfully executed OpenSearch DSL Query {len(dsl_search_results)}"
                " hits found"
            )
        else:
            self.output_message: str = "No results found for the provided DSL query."

        if dsl_search_results:
            flat_results: List[SingleJson] = []
            for dsl_result in dsl_search_results:
                flat_result: SingleJson = dsl_result.to_flat()
                flat_results.append(flat_result)

            csv_output: str = construct_csv(flat_results)
            self.soar_action.result.add_data_table(
                f"Results - Total {len(dsl_search_results)}", csv_output
            )
            self.soar_action.result.add_result_json(
                [dsl_result.to_json() for dsl_result in dsl_search_results]
            )

        self.result_value: bool = True


def main() -> NoReturn:
    DslSearch().run()


if __name__ == "__main__":
    main()
