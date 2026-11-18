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

from ..core.api_utils import build_query
from ..core.base_action import BaseAction
from ..core.constants import (
    EMAIL_ENTITY_TYPE,
    INTEGRATION_DISPLAY_NAME,
    SEARCH_ENTITY_GRAPHS_SCRIPT_NAME,
    SORT_FIELD_MAPPING,
)
from ..core.exceptions import GoogleThreatIntelligenceBadRequestException
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon import validation
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import convert_list_to_comma_string
from TIPCommon.utils import is_empty_string_or_none
from ..core.utils import get_entity_type

SUCCESS_MESSAGE = ""
ERROR_MESSAGE = f"Error executing action {SEARCH_ENTITY_GRAPHS_SCRIPT_NAME}."
NO_GRAPHS_FOUND_MESSAGE = "No graphs were found for the provided entities."
SUPPORTED_ENTITY_TYPES = [
    EntityTypes.FILEHASH,
    EntityTypes.URL,
    EntityTypes.ADDRESS,
    EntityTypes.HOSTNAME,
    EntityTypes.DOMAIN,
    EntityTypes.THREATACTOR,
    EntityTypes.USER,
    EMAIL_ENTITY_TYPE,
]


class SearchEntityGraphsDetails(BaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = SUCCESS_MESSAGE
        self.error_output_message = ERROR_MESSAGE
        self.result_value = True
        self.json_results = {}
        self.suitable_entities = [
            entity
            for entity in self._soar_action.target_entities
            if get_entity_type(entity) in SUPPORTED_ENTITY_TYPES
        ]

    def _extract_action_parameters(self) -> None:
        self.params.sort_field = extract_action_param(
            self.soar_action,
            param_name="Sort Field",
            print_value=True,
        )
        self.params.max_graphs_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Graphs To Return",
            is_mandatory=True,
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator = validation.ParameterValidator(self.soar_action)

        if not is_empty_string_or_none(self.params.max_graphs_to_return):
            self.params.max_graphs_to_return = validator.validate_positive(
                param_name="Max Graphs To Return",
                value=self.params.max_graphs_to_return,
                print_value=False,
            )

    def _perform_action(self, _=None) -> None:
        self.api_client.test_connectivity()
        if not self.suitable_entities:
            self.output_message = NO_GRAPHS_FOUND_MESSAGE
            self.result_value = False
            return

        self.logger.info(
            f"Processing entities: "
            f"{convert_list_to_comma_string(self.suitable_entities)}"
        )
        query = build_query(self.suitable_entities)
        graphs = []

        try:
            graphs = self.api_client.search_graphs(
                query,
                SORT_FIELD_MAPPING.get(self.params.sort_field),
                self.params.max_graphs_to_return,
            )
        except GoogleThreatIntelligenceBadRequestException as e:
            self.output_message += (
                "Action wasn't able to successfully return graph based on the "
                f"provided entities in {INTEGRATION_DISPLAY_NAME}. Reason: {e}"
            )
            self.result_value = False
            raise

        if not graphs:
            self.output_message = NO_GRAPHS_FOUND_MESSAGE
            self.result_value = False
            return

        self.output_message = (
            f"Successfully returned graphs based on the provided entities in "
            f"{INTEGRATION_DISPLAY_NAME}."
        )

        self.logger.info("Adding graphs to JSON results")
        self.json_results = [graph.to_json_shorten() for graph in graphs]


def main() -> None:
    SearchEntityGraphsDetails(SEARCH_ENTITY_GRAPHS_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
