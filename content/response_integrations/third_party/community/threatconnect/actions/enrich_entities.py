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

import copy
from typing import TYPE_CHECKING, Any

from TIPCommon.base.action.data_models import EntityTypesEnum
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import (
    add_prefix_to_dict_keys,
    dict_to_flat,
    string_to_multi_value,
)

from ..core.base_action import ThreatConnectAction
from ..core.constants import ENRICH_ENTITIES_SCRIPT_NAME

if TYPE_CHECKING:
    from TIPCommon.types import Entity, SingleJson


TYPE_MAPPING = {
    "Address": "address",
    "EmailAddress": "address",
    "File": "file",
    "Host": "host",
    "URL": "url",
}


class EnrichEntities(ThreatConnectAction):
    """Action to enrich IP addresses, hosts, URLs and hashes using
    ThreatConnect V3 REST API.
    """

    def __init__(self) -> None:
        super().__init__(ENRICH_ENTITIES_SCRIPT_NAME)

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
            print_value=True,
        )
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

        is_file = current_entity.entity_type in [
            EntityTypesEnum.FILE_HASH,
            EntityTypesEnum.FILE_HASH.value,
        ]
        if is_file:
            original_identifier = original_identifier.upper()

        raw_indicators = self.api_client.get_indicator_info(
            indicator_value=original_identifier,
            owner_names=self.params.owner_names_list,
        )

        if not raw_indicators:
            return

        result_list = []
        for indicator in raw_indicators:
            mapped_data = indicator.to_v2_json(original_identifier)
            result_list.append(mapped_data)

            self._add_insight(mapped_data, current_entity)
            self._enrich_entity(mapped_data, current_entity)

        if result_list:
            self.json_results[current_entity.identifier] = result_list
            self.entities_to_update.append(current_entity)

    def _get_target_item(self, indicator_data: SingleJson) -> SingleJson | None:
        general_block = indicator_data.get("general", {})

        if not isinstance(general_block, dict):
            return None

        v2_type = "file" if "file" in general_block else next(iter(general_block), None)

        if not v2_type or v2_type not in general_block:
            return None

        target_item = general_block[v2_type]
        return target_item if isinstance(target_item, dict) else None

    def _process_indicators_metadata(
        self,
        target_item: SingleJson,
        entity: Entity
    ) -> None:
        link = target_item.get("webLink")

        if link:
            self.soar_action.result.add_entity_link(entity.identifier, link)

        rating = target_item.get("threatAssessRating", 0.0)
        score = target_item.get("threatAssessScore", 0)

        if (rating and rating > 1) or (score and score >= 300):
            entity.is_suspicious = True

    def _build_enrichment_report(self, indicator_data: SingleJson) -> SingleJson:
        flat_data = copy.deepcopy(indicator_data)
        tags_envelope = flat_data.get("tags")

        if isinstance(tags_envelope, dict) and "tag" in tags_envelope:
            raw_tags = tags_envelope.get("tag", []) or []
            flat_data["tags"] = [
                tag.get("name")
                for tag in raw_tags
                if isinstance(tag, dict) and tag.get("name")
            ]

        flat_report = add_prefix_to_dict_keys(dict_to_flat(flat_data), "TC")
        flat_tags_list = flat_data.get("tags")

        if isinstance(flat_tags_list, list) and flat_tags_list:
            flat_report["TC_tags"] = flat_tags_list

        return flat_report

    def _merge_existing_property(self, entity: Entity, key: str, value: Any) -> None:
        existing_val = entity.additional_properties[key]

        if isinstance(existing_val, str):
            working_list = existing_val.split(", ") if existing_val else []
        elif isinstance(existing_val, list):
            working_list = [str(item) for item in existing_val]
        else:
            working_list = (
                [str(existing_val)]
                if existing_val is not None
                else []
            )

        working_list = [item.strip() for item in working_list if item]
        new_items = value if isinstance(value, list) else [value]

        for item in new_items:
            if item is not None:
                str_item = str(item).strip()
                if str_item and str_item not in working_list:
                    working_list.append(str_item)

        entity.additional_properties[key] = (
            ", ".join(working_list) if working_list else ""
        )

    def _set_new_property(self, entity: Entity, key: str, value: Any) -> None:
        if isinstance(value, list):
            entity.additional_properties[key] = ", ".join(
                str(item) for item in value if item is not None
            )
        else:
            entity.additional_properties[key] = str(value) if value is not None else ""

    def _merge_enrichment_properties(
        self,
        flat_report: SingleJson,
        entity: Entity
    ) -> None:
        for k, v in flat_report.items():
            if k in entity.additional_properties:
                self._merge_existing_property(entity, k, v)
            else:
                self._set_new_property(entity, k, v)

    def _enrich_entity(self, indicator_data: SingleJson, entity: Entity) -> None:
        target_item = self._get_target_item(indicator_data)
        if not target_item:
            return

        self._process_indicators_metadata(target_item, entity)
        flat_report = self._build_enrichment_report(indicator_data)
        self._merge_enrichment_properties(flat_report, entity)
        entity.is_enriched = True

    def _get_insight_target_data(self, indicator_data: SingleJson) -> SingleJson:
        general_block = indicator_data.get("general", {})
        if not isinstance(general_block, dict):
            return {}
        v2_type = "file" if "file" in general_block else next(iter(general_block), None)
        if not v2_type:
            return {}
        target_data = general_block.get(v2_type, {})
        return target_data if isinstance(target_data, dict) else {}

    def _parse_insight_tags(self, indicator_data: SingleJson) -> str:
        tags_envelope = indicator_data.get("tags")
        parsed_tags = []

        if isinstance(tags_envelope, dict):
            tags_list = tags_envelope.get("tag", []) or []
        else:
            tags_list = tags_envelope if isinstance(tags_envelope, list) else []

        for tag in tags_list:
            if isinstance(tag, dict):
                name = tag.get("name")
                if name:
                    parsed_tags.append(str(name).strip())
            elif tag is not None:
                parsed_tags.append(str(tag).strip())

        return "| ".join(filter(None, parsed_tags))

    def _build_insight_message(
        self,
        target_data: SingleJson,
        tags: str
    ) -> str:
        threat_asset_rating = target_data.get("threatAssessRating")
        confidence = target_data.get("confidence")
        description = target_data.get("description")

        insight_msg = ""
        insight_msg += (
            f"Threat asset rating: {threat_asset_rating}.\n"
            if threat_asset_rating is not None
            else "No threat asset rating.\n"
        )
        insight_msg += (
            f"Confidence: {confidence}.\n"
            if confidence is not None
            else "Confidence: 0.\n"
        )
        insight_msg += (
            f"Description: {description}.\n"
            if description
            else "No description.\n"
        )
        insight_msg += f"Tags: {tags}.\n" if tags else "No tags.\n"
        return insight_msg

    def _add_insight(self, indicator_data: SingleJson, entity: Entity) -> None:
        target_data = self._get_insight_target_data(indicator_data)
        tags = self._parse_insight_tags(indicator_data)
        insight_msg = self._build_insight_message(target_data, tags)

        self.soar_action.add_entity_insight(
            entity,
            insight_msg,
            triggered_by="ThreatConnect",
        )

    def _finalize_action_on_success(self) -> None:
        if self.entities_to_update:
            success_ids = ", ".join(e.identifier for e in self.entities_to_update)
            self.output_message = (
                "Successfully enriched the following entities using ThreatConnect: "
                f"{success_ids}"
            )
            enriched_identifiers = {e.identifier for e in self.entities_to_update}
            failed_entities = [
                e.identifier
                for e in self.soar_action.target_entities
                if e.identifier not in enriched_identifiers
            ]
            if failed_entities:
                failed_ids = ", ".join(failed_entities)
                self.output_message += (
                    "\nAction wasn't able to enrich the following entities using "
                    f"ThreatConnect: {failed_ids}"
                )
            self.result_value = True
        else:
            self.output_message = "None of the provided entities were enriched."
            self.result_value = False


def main() -> None:
    """Enrich Entities action entry point."""
    EnrichEntities().run()


if __name__ == "__main__":
    main()
