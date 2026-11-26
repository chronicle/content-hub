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
from TIPCommon.extraction import extract_action_param
from TIPCommon.base.action import Action
from TIPCommon.transformation import (
    convert_dict_to_json_result_dict,
    string_to_multi_value,
)

from ..core.action_init import create_api_client
from ..core.consts import GET_GROUP_DETAILS_SCRIPT_NAME
from ..core.exceptions import (
    GSuiteValidationException,
    GSuiteNotFoundException,
    GSuiteManagerError,
)
from ..core.GSuiteManager import GSuiteManager
from soar_sdk.SiemplifyDataModel import EntityTypes


SUPPORTED_ENTITY_TYPES = [EntityTypes.USER]


class GetGroupDetails(Action):
    def __init__(self) -> None:
        super().__init__(GET_GROUP_DETAILS_SCRIPT_NAME)
        self.output_message = ""
        self.result_value = True
        self.error_output_message = (
            f'Error executing action "{GET_GROUP_DETAILS_SCRIPT_NAME}".'
        )

    def _extract_action_parameters(self) -> None:
        self.params.group_identifiers = string_to_multi_value(
            extract_action_param(
                self.soar_action,
                param_name="Group Email Addresses",
                is_mandatory=True,
                print_value=True,
            )
        )

    def _init_api_clients(self) -> GSuiteManager:
        return create_api_client(self.soar_action)

    def _perform_action(self, _: None) -> None:
        results = {}
        not_found_groups = []
        for group_identifier in self.params.group_identifiers:
            try:
                group_settings = self.api_client.get_group_settings(group_identifier)
            except (
                GSuiteValidationException,
                GSuiteNotFoundException,
                GSuiteManagerError,
            ):
                not_found_groups.append(group_identifier)
                self.logger.info(f"Unable to find data about group: {group_identifier}")
                continue

            results[group_identifier] = group_settings.as_json()

        if results:
            self.output_message += (
                "Successfully enriched the following groups using information "
                "from Google Workspace: " + ", ".join(group for group in results) + "\n"
            )
            json_result = convert_dict_to_json_result_dict(results)
            self.soar_action.result.add_result_json(json_result)
        if len(not_found_groups) == len(self.params.group_identifiers):
            self.output_message += "None of the groups were enriched.\n"
            self.result_value = False
        elif not_found_groups:
            self.output_message += (
                "Action wasn't able to enrich the following group using information "
                "from Google Workspace: "
                + ", ".join(group for group in not_found_groups)
                + "\n"
            )


def main() -> None:
    GetGroupDetails().run()


if __name__ == "__main__":
    main()
