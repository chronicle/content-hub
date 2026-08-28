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
from soar_sdk.SiemplifyUtils import create_entity_json_result_object
from TIPCommon.transformation import flat_dict_to_csv, dict_to_flat

from ..core.base_action import ZscalerBaseAction
from ..core.constants import LOOKUP_URL_SCRIPT_NAME
from ..core.exceptions import ZscalerManagerError

if TYPE_CHECKING:
    from soar_sdk.SiemplifyDataModel import Entity


def match_entity(zscaler_manager, entities, entity_name):
    for entity in entities:
        if (
            zscaler_manager.validate_and_extract_url(entity.identifier.lower())
            == entity_name
        ):
            return entity

    raise ZscalerManagerError(f"No matching entity was found for {entity_name}")


class LookupEntityAction(ZscalerBaseAction):
    def __init__(self) -> None:
        super().__init__(LOOKUP_URL_SCRIPT_NAME)
        self.json_results: list = []
        self.output_message: str = ""
        self.result_value: bool = False

    def _perform_action(self, _=None) -> None:
        """Perform the lookup action."""
        entities_to_look_for, urls_to_look_for = self._extract_target_urls()

        if not urls_to_look_for:
            self.output_message = "No entities were found in Zscaler."
            self.result_value = False
            return

        self.logger.info("Looking for the URLs in Zscaler.")
        urls_info = self.api_client.lookup_urls(urls_to_look_for)

        urls, errors = self._process_lookup_results(urls_info, entities_to_look_for)
        self._build_output_message(urls, errors)

    def _extract_target_urls(self) -> tuple[list[Entity], list[str]]:
        """Extract target URLs from entities."""
        entities_to_look_for = []
        urls_to_look_for = []

        for entity in self.soar_action.target_entities:
            if entity.entity_type in [
                EntityTypes.URL,
                EntityTypes.HOSTNAME,
                EntityTypes.DOMAIN,
            ]:
                entities_to_look_for.append(entity)
                normalized_url = self.api_client.validate_and_extract_url(
                    entity.identifier.lower()
                )
                self.logger.info(f"Adding {normalized_url} to urls list to look for.")
                urls_to_look_for.append(normalized_url)

        return entities_to_look_for, urls_to_look_for

    def _process_lookup_results(
        self, urls_info: list[dict], entities_to_look_for: list[Entity]
    ) -> tuple[list[str], list[str]]:
        """Process lookup results and update results."""
        urls = []
        errors = []

        if urls_info:
            for url_info in urls_info:
                entity_name = url_info.get("url")
                self.logger.info(f"Found info for {entity_name}")
                try:
                    entity = match_entity(
                        self.api_client, entities_to_look_for, url_info.get("url")
                    )
                    urls.append(entity.identifier)
                    self.result_value = True
                    self.json_results.append(
                        create_entity_json_result_object(entity.identifier, url_info)
                    )

                    flat_info = dict_to_flat(url_info)
                    self.soar_action.result.add_entity_table(
                        f"{entity.identifier} Categorization",
                        flat_dict_to_csv(flat_info),
                    )
                except ZscalerManagerError as error:

                    self.logger.error(
                        f"An error occurred on entity: {entity_name}.\n{str(error)}."
                    )
                    self.logger.exception(error)
                    errors.append(entity_name)

        return urls, errors

    def _build_output_message(self, urls: list[str], errors: list[str]) -> None:
        """Build output message based on results."""
        if urls:
            self.output_message += (
                "The following entities found in Zscaler: \n{}".format("\n".join(urls))
            )
            self.result_value = True

        if errors:
            self.output_message += (
                "\nErrors occurred on the following entities: \n"
                "{}\nCheck logs for more details".format("\n".join(errors))
            )

        if not urls and not errors:
            self.output_message = "No entities were found in Zscaler."
            self.result_value = False


def main() -> None:
    LookupEntityAction().run()


if __name__ == "__main__":
    main()
