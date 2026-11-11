from __future__ import annotations

import re
from typing import Any

from requests.exceptions import HTTPError

from google_threat_intelligence.core.exceptions import GoogleThreatIntelligenceExceptions
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon.base.action import EntityTypesEnum
from TIPCommon.exceptions import ParameterValidationError, SDKWrapperError
from TIPCommon.extraction import extract_action_param
from TIPCommon.utils import get_entity_original_identifier
from TIPCommon.validation import ParameterValidator

from google_threat_intelligence.core.data_models import EntityAssociations, IOCRelatedAssociations
from google_threat_intelligence.core.base_action import BaseAction
from google_threat_intelligence.core.constants import (
    EXTEND_GRAPH_URL,
    INTEGRATION_DISPLAY_NAME,
    GET_RELATED_ASSOCIATIONS_SCRIPT_NAME,
    MAX_ASSOCIATIONS_TO_RETURN_DEFAULT_VALUE,
    MAX_ASSOCIATIONS_TO_RETURN_LIMIT,
    MIN_ASSOCIATIONS_TO_RETURN_LIMIT,
)
from google_threat_intelligence.core.utils import (
    get_entity_type,
    prepare_entity_for_manager,
    map_by_case_insensitive_keys,
)


SUPPORTED_ENTITY_TYPES = [
    EntityTypes.URL,
    EntityTypes.ADDRESS,
    EntityTypes.HOSTNAME,
    EntityTypes.DOMAIN,
    EntityTypes.FILEHASH,
]

ENTITY_TYPE_TO_IOC_MAPPING = {
    EntityTypes.URL: "urls",
    EntityTypes.HOSTNAME: "domains",
    EntityTypes.DOMAIN: "domains",
    EntityTypes.ADDRESS: "ip_addresses",
    EntityTypes.FILEHASH: "files",
}

COLLECTION_TYPE_TO_IOC_MAPPING = {
    "Report": "report",
    "Campaign": "campaign",
    "Collection": "collection",
    "Malware Family": "malware-family",
    "Vulnerability": "vulnerability",
    "Threat Actor": "threat-actor",
}

IOC_COLLECTION_TYPE_TO_ENTITY_TYPE_MAPPING = {
    "threat-actor": EntityTypesEnum.THREAT_ACTOR,
    "campaign": EntityTypesEnum.THREAT_CAMPAIGN,
    "vulnerability": EntityTypesEnum.CVE,
}


class GetRelatedAssociations(BaseAction):
    def __init__(self):
        """Initialize the GetRelatedAssociations action."""
        super().__init__(GET_RELATED_ASSOCIATIONS_SCRIPT_NAME)
        self._target_entities_keys = self._get_target_entities_keys()

    def _extract_action_parameters(self) -> None:
        """Extract and store action parameters from the SOAR."""
        self.params.association_types = extract_action_param(
            self.soar_action,
            param_name="Association Types",
            remove_whitespaces=False,
            print_value=True,
        )
        self.params.create_entity = extract_action_param(
            self.soar_action,
            param_name="Create Entity",
            print_value=True,
            input_type=bool,
        )
        self.params.max_associations_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Associations To Return",
            print_value=True,
            input_type=int,
            default_value=MAX_ASSOCIATIONS_TO_RETURN_DEFAULT_VALUE,
        )

    def _validate_params(self) -> None:
        """Validate the extracted action parameters."""
        validator: ParameterValidator = ParameterValidator(self.soar_action)

        validator.validate_range(
            param_name="Max Associations To Return",
            value=self.params.max_associations_to_return,
            min_limit=MIN_ASSOCIATIONS_TO_RETURN_LIMIT,
            max_limit=MAX_ASSOCIATIONS_TO_RETURN_LIMIT,
        )

        self.params.association_types = validator.validate_csv(
            param_name="Association Types",
            csv_string=self.params.association_types,
            print_value=True,
        )
        try:
            self.params.association_types = map_by_case_insensitive_keys(
                keys=self.params.association_types,
                mapping=COLLECTION_TYPE_TO_IOC_MAPPING,
            # Empty "Association Types" param means that a user wants to get all of them
            ) or list(COLLECTION_TYPE_TO_IOC_MAPPING.values())
        except ValueError as e:
            raise ParameterValidationError(
                param_name="Association Types",
                value=self.params.association_types,
                message=str(e),
                exception=e,
            ) from e

    @staticmethod
    def _normalize_entity_id(entity_id: str) -> str:
        """Normalize an entity identifier for consistent matching."""
        return entity_id.lower()

    def _get_target_entities_keys(self) -> set[tuple[str, str]]:
        """Get a set of (normalized_identifier, type) for all target entities."""
        return {
            (
                self._normalize_entity_id(get_entity_original_identifier(entity)),
                get_entity_type(entity)
            )
            for entity in self.soar_action.target_entities
            if get_entity_original_identifier(entity)
        }

    def _update_target_entities_keys(self, entity_id: str, entity_type: str) -> None:
        """Add a new entity's key to the set of tracked entities."""
        self._target_entities_keys.add(
            (self._normalize_entity_id(entity_id), entity_type)
        )

    def _check_if_entity_exists(
        self, entity_id: str, entity_type: EntityTypesEnum
    ) -> bool:
        """Check if an entity already exists in the case based on its key."""
        return (
            self._normalize_entity_id(entity_id),
            entity_type.value
        ) in self._target_entities_keys

    def _get_supported_entities(self) -> dict[str, Any]:
        """Filter target entities to return only those supported by this action."""
        return {
            get_entity_original_identifier(entity): entity
            for entity in self.soar_action.target_entities
            if get_entity_type(entity) in SUPPORTED_ENTITY_TYPES
        }

    def _get_related_associations(
        self,
        supported_entities: dict[str, Any],
    ) -> EntityAssociations:
        """Fetch related associations from the API for each supported entity."""
        entities_with_associations = {}
        entities_without_associations = []
        failed_entities = []

        for entity_id, entity in supported_entities.items():
            try:
                association_items = self.api_client.get_related_associations(
                    ENTITY_TYPE_TO_IOC_MAPPING[get_entity_type(entity)],
                    prepare_entity_for_manager(entity),
                    association_types=self.params.association_types,
                    limit=self.params.max_associations_to_return,
                )

                if "report" in self.params.association_types:
                    reports_limit = (
                        self.params.max_associations_to_return - len(association_items)
                    )
                    if reports_limit > 0:
                        association_reports = self.api_client.get_related_associations(
                            ENTITY_TYPE_TO_IOC_MAPPING[get_entity_type(entity)],
                            prepare_entity_for_manager(entity),
                            relationship="reports",
                            limit=reports_limit,
                        )

                        association_items.extend(association_reports)

                result = IOCRelatedAssociations.from_association_items(
                    associations=association_items,
                )

                if result.associations:
                    entities_with_associations[entity_id] = result
                else:
                    entities_without_associations.append(entity_id)

            except GoogleThreatIntelligenceExceptions as e:
                failed_entities.append(entity_id)
                self.logger.error(f"Error processing entity {entity_id}: {e}")
                self.logger.exception(e)

        return EntityAssociations(
            entities_with_associations=entities_with_associations,
            entities_without_associations=entities_without_associations,
            failed_entities=failed_entities,
        )

    def _create_entity_relationship(
        self,
        entity_name: str,
        entity_type: str,
        linked_entity_name: str,
    ) -> None:
        """Create a visual relationship link between two entities in the Platform."""
        payload = {
            "caseId": self.soar_action.case_id,
            "alertIdentifier": self.soar_action.current_alert.identifier,
            "entityType": entity_type,
            "isPrimaryLink": False,
            "isDirectional": False,
            "typesToConnect": [],
            "entityToConnectRegEx": f"{re.escape(str(linked_entity_name))}$",
            "entityIdentifier": entity_name,
        }
        created_entity_response = self.soar_action.session.post(
            EXTEND_GRAPH_URL.format(self.soar_action.API_ROOT), json=payload
        )
        created_entity_response.raise_for_status()

    def _create_entity_for_association(
        self,
        entities: dict[str, Any],
        associations: dict[str, Any]
    ) -> None:
        """Create and link new entities in the Platform for found associations."""
        for parent_entity_id, associations_obj in associations.items():
            for association in associations_obj.associations:
                entity_type = IOC_COLLECTION_TYPE_TO_ENTITY_TYPE_MAPPING.get(
                    association.attributes.collection_type
                )
                if not entity_type:
                    continue

                association_id = association.attributes.name
                if not association_id:
                    raise GoogleThreatIntelligenceExceptions(
                        "Can't create Entity from Association. Association ID is "
                        "undefined"
                    )

                try:
                    if not self._check_if_entity_exists(association_id, entity_type):
                        self._add_entity_to_case(
                            entity_identifier=association_id,
                            entity_type=entity_type,
                            is_suspicious=False,
                            is_internal=False,
                            is_enriched=False,
                            is_vulnerable=False,
                            properties={},
                        )
                        self._update_target_entities_keys(
                            entity_id=association_id, entity_type=entity_type.value
                        )

                    self._create_entity_relationship(
                        entity_name=parent_entity_id,
                        entity_type=get_entity_type(entities[parent_entity_id]),
                        linked_entity_name=association_id,
                    )
                except SDKWrapperError as e:
                    self.logger.error(
                        f"Error creating new entity {association_id}: {e}"
                    )
                except HTTPError as e:
                    self.logger.error(
                        f"Error creating relationship "
                        f"[{parent_entity_id} -> {association_id}]: {e}"
                    )

    def _set_output_message(
        self,
        entities_with_associations: list[str],
        entities_without_associations: list[str],
        failed_entities: list[str],
    ) -> None:
        """Construct a comprehensive output message for the Platform action result."""
        messages = []

        if entities_with_associations:
            messages.append(
                f"Successfully found associations for the following entities "
                f"in {INTEGRATION_DISPLAY_NAME}:\n"
                f"{', '.join(entities_with_associations)}"
            )

        if entities_without_associations or failed_entities:
            # When we have both entities with associations and entities without them
            # (or with errors), we need to display both results.
            if entities_with_associations:
                messages.append(
                    f"No related associations were found for the following entities "
                    f"in {INTEGRATION_DISPLAY_NAME}:\n"
                    f"{', '.join(entities_without_associations + failed_entities)}"
                )
            # When all entities have failed or have no associations,
            # we do not need to display them.
            else:
                messages.append(
                    "No related associations were found for the provided entities "
                    f"in {INTEGRATION_DISPLAY_NAME}."
                )

        if not messages:
            messages.append(
                f"No supported entities were found to process "
                f"in {INTEGRATION_DISPLAY_NAME}."
            )

        self.output_message = "\n\n".join(messages)

    def _set_json_result(
        self,
        entities: dict[str, IOCRelatedAssociations],
    ) -> None:
        """Construct a list of items grouped by collection type."""
        self.json_results = [
            {
                "Entity": entity_id,
                "EntityResult": associations.group_by_collection_type(),
            }
            for entity_id, associations in entities.items()
        ]
        self.result_value = bool(self.json_results)

    def _perform_action(self, _=None) -> None:
        """Execute the main logic of the action."""
        self.api_client.test_connectivity()

        entities = self._get_supported_entities()
        associations = self._get_related_associations(
            supported_entities=entities
        )

        if self.params.create_entity:
            self._create_entity_for_association(
                entities=entities,
                associations=associations.entities_with_associations
            )

        self._set_output_message(
            entities_with_associations=list(
                associations.entities_with_associations.keys()
            ),
            entities_without_associations=associations.entities_without_associations,
            failed_entities=associations.failed_entities,
        )

        self._set_json_result(
            entities=associations.entities_with_associations
        )


def main() -> None:
    """Main function to run the action."""
    GetRelatedAssociations().run()


if __name__ == "__main__":
    main()
