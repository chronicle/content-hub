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

from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import string_to_multi_value

from ..core.base_action import CloudIdentityAction
from ..core.consts import INTEGRATION_NAME

if TYPE_CHECKING:
    from typing import NoReturn

    from TIPCommon.types import Entity


class AddEntityToDetectorURLList(CloudIdentityAction):
    def __init__(self) -> None:
        super().__init__(f"{INTEGRATION_NAME} - AddEntityToDetectorURLList")

    def _extract_action_parameters(self) -> None:
        self.params.policy_id = extract_action_param(
            self.soar_action,
            param_name="Detector Policy ID",
            is_mandatory=True,
            print_value=True,
        )
        urls_str = extract_action_param(
            self.soar_action,
            param_name="URL",
            print_value=True,
        )
        self.params.urls = string_to_multi_value(urls_str)

        domains_str = extract_action_param(
            self.soar_action,
            param_name="Domain",
            print_value=True,
        )
        self.params.domains = string_to_multi_value(domains_str)

    def _perform_action(self, _: Entity | None = None) -> None:
        all_urls_to_block: list[str] = []
        all_urls_to_block.extend(self.params.urls)
        all_urls_to_block.extend(self.params.domains)

        supported_entity_types = [EntityTypes.URL, EntityTypes.HOSTNAME]
        all_urls_to_block.extend(
            entity.identifier
            for entity in self.soar_action.target_entities
            if entity.entity_type in supported_entity_types
        )

        if not all_urls_to_block:
            self.result_value = False
            self.output_message = "No entities, domains or url provided to block"
            return

        self.logger.info("Successfully identified URLs to block.")

        updated_policy = self.api_client.update_url_list_detector_policy(
            policy_id=self.params.policy_id, urls=all_urls_to_block
        )
        self.json_results = updated_policy.to_dict()

        self.result_value = True
        urls_str = ", ".join(all_urls_to_block)
        self.output_message = f"Successfully blocked the following URLs using Cloud Identity: {urls_str}"


def main() -> NoReturn:
    """Run the AddEntityToDetectorURLList action."""
    AddEntityToDetectorURLList().run()


if __name__ == "__main__":
    main()
