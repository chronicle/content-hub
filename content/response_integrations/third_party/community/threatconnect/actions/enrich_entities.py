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

"""ThreatConnect Enrich Entities Action script."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from TIPCommon.base.action.data_models import EntityTypesEnum
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import add_prefix_to_dict_keys, dict_to_flat, string_to_multi_value

from ..core.base_action import ThreatConnectAction

if TYPE_CHECKING:
    from TIPCommon.types import Entity

    from ..core.api.api_client import ThreatConnectApiClient

ACTION_NAME = "ThreatConnect - Enrich Entities"

TYPE_MAPPING = {
    "Address": "address",
    "EmailAddress": "address",
    "File": "file",
    "Host": "host",
    "URL": "url",
}


class EnrichEntities(ThreatConnectAction):
    """Action to enrich IP addresses, hosts, URLs and hashes using ThreatConnect V3 REST API."""

    def __init__(self) -> None:
        super().__init__(ACTION_NAME)
        self.enriched_entities: list[Entity] = []
        self.json_results: dict[str, Any] = {}

    def _get_entity_types(self) -> list[EntityTypesEnum]:
        """Specify the entity types supported by this action."""
        return [
            EntityTypesEnum.ADDRESS,
            EntityTypesEnum.FILE_HASH,
            EntityTypesEnum.URL,
            EntityTypesEnum.HOST_NAME,
        ]

    def _extract_action_parameters(self) -> None:
        self.params.owner_names = extract_action_param(
            self.soar_action,
            param_name="Owner Name",
            is_mandatory=False,
            print_value=True,
        )

    def _validate_params(self) -> None:
        self.params.owner_names_list = string_to_multi_value(
            self.params.owner_names,
            only_unique=True,
        )

    def _perform_action(self, current_entity: Entity | None) -> None:
        """Enrich a single entity."""
        if current_entity is None:
            return

        original_identifier = current_entity.additional_properties.get(
            "OriginalIdentifier",
            current_entity.identifier.lower(),
        )

        if current_entity.entity_type == EntityTypesEnum.FILE_HASH:
            original_identifier = original_identifier.upper()

        client: ThreatConnectApiClient = self.api_client  # type: ignore[assignment]
        raw_indicators = client.get_indicator_info(
            indicator_value=original_identifier,
            owner_names=self.params.owner_names_list,
        )

        if not raw_indicators:
            return

        result_list = []
        for indicator in raw_indicators:
            mapped_data = indicator.to_v2_json(original_identifier)
            result_list.append(mapped_data)

            self._enrich_entity(mapped_data, current_entity)
            self._add_insight(mapped_data, current_entity)

        if result_list:
            self.json_results[current_entity.identifier] = result_list
            self.enriched_entities.append(current_entity)
            self.entities_to_update.append(current_entity)

    def _enrich_entity(self, indicator_data: dict, entity: Entity) -> None:
        v3_type = indicator_data["general"].keys()
        v2_type = list(v3_type)[0]

        link = indicator_data["general"][v2_type].get("webLink")
        if link:
            self.soar_action.result.add_entity_link(entity.identifier, link)

        rating = indicator_data["general"][v2_type].get("threatAssessRating", 0)
        if rating and rating > 1:
            entity.is_suspicious = True

        flat_report = dict_to_flat(indicator_data)
        flat_report = add_prefix_to_dict_keys(flat_report, "TC")
        entity.additional_properties.update(flat_report)
        entity.is_enriched = True

    def _add_insight(self, indicator_data: dict, entity: Entity) -> None:
        v3_type = indicator_data["general"].keys()
        v2_type = list(v3_type)[0]

        threat_asset_rating = indicator_data.get("general", {}).get(v2_type, {}).get("threatAssessRating")
        confidence = indicator_data.get("general", {}).get(v2_type, {}).get("confidence")
        description = indicator_data.get("general", {}).get(v2_type, {}).get("description")
        tags_list = indicator_data.get("tags") or []
        tags = "| ".join(str(tag) for tag in tags_list)

        insight_msg = ""
        insight_msg += (
            f"Threat asset rating: {threat_asset_rating}. \n" if threat_asset_rating else "No threat asset rating. \n"
        )
        insight_msg += f"Confidence: {confidence}. \n" if confidence else "Confidence: 0 \n"
        insight_msg += f"Description: {description}. \n" if description else "No description. \n"
        insight_msg += f"Tags: {tags}. \n" if tags else "No tags. \n"

        self.soar_action.add_entity_insight(
            entity,
            insight_msg,
            triggered_by="ThreatConnect",
        )

    def _finalize_action_on_success(self) -> None:
        if self.enriched_entities:
            self.output_message = (
                "Following entities were enriched by ThreatConnect. \n"
                f"'{', '.join(e.identifier for e in self.enriched_entities)}'"
            )
            self.result_value = True
            pass
        else:
            self.output_message = "No entities were enriched."
            self.result_value = False


def main() -> None:
    """Enrich Entities action entry point."""
    EnrichEntities().run()


if __name__ == "__main__":
    main()
