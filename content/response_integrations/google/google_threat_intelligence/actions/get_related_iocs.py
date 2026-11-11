from __future__ import annotations

from google_threat_intelligence.core.base_action import BaseAction
from google_threat_intelligence.core.constants import (
    GET_RELATED_IOCS_SCRIPT_NAME,
    INTEGRATION_DISPLAY_NAME,
    POSSIBLE_IOC_TYPES,
    RELATIONSHIP_MAP,
)
from google_threat_intelligence.core.exceptions import (
    GoogleThreatIntelligenceExceptions,
    GoogleThreatIntelligencePermissionException,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict
from TIPCommon import validation
from TIPCommon.extraction import extract_action_param
from TIPCommon.utils import is_empty_string_or_none
from google_threat_intelligence.core.utils import (
    get_entity_original_identifier,
    get_entity_type,
    get_threat_actor_id_by_origin,
    prepare_entity_for_manager,
)

entity_type_map = {
    EntityTypes.FILEHASH: "files",
    EntityTypes.URL: "urls",
    EntityTypes.ADDRESS: "ip_addresses",
    EntityTypes.HOSTNAME: "domains",
    EntityTypes.DOMAIN: "domains",
    EntityTypes.THREATACTOR: "collections",
}

SUCCESS_MESSAGE = ""
ERROR_MESSAGE = f"Error executing action {GET_RELATED_IOCS_SCRIPT_NAME}."
SUPPORTED_ENTITY_TYPES = [
    EntityTypes.FILEHASH,
    EntityTypes.URL,
    EntityTypes.ADDRESS,
    EntityTypes.HOSTNAME,
    EntityTypes.DOMAIN,
    EntityTypes.THREATACTOR,
]


class GetRelatedIOCs(BaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = SUCCESS_MESSAGE
        self.error_output_message = ERROR_MESSAGE
        self.result_value = True
        self.json_results = {}
        self.found_entities = []
        self.not_found_entities = []
        self.suitable_entities = [
            entity
            for entity in self._soar_action.target_entities
            if get_entity_type(entity) in SUPPORTED_ENTITY_TYPES
        ]

    def _extract_action_parameters(self) -> None:
        self.params.ioc_types = extract_action_param(
            self.soar_action,
            param_name="IOC Types",
            is_mandatory=True,
            print_value=True,
        )
        self.params.max_iocs_to_return = extract_action_param(
            self.soar_action,
            param_name="Max IOCs To Return",
            is_mandatory=True,
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator = validation.ParameterValidator(self.soar_action)

        if not is_empty_string_or_none(self.params.max_iocs_to_return):
            self.params.max_iocs_to_return = validator.validate_positive(
                param_name="Max IOCs To Return",
                value=self.params.max_iocs_to_return,
                print_value=False,
            )

        self.params.ioc_types = validator.validate_csv(
            param_name="IOC Types",
            csv_string=self.params.ioc_types,
            possible_values=POSSIBLE_IOC_TYPES,
            print_value=False,
        )

    def _perform_action(self, _=None) -> None:
        self.api_client.test_connectivity()
        for entity in self.suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)
            identifier = prepare_entity_for_manager(entity)
            entity_type = get_entity_type(entity)

            ioc_types = set(self.params.ioc_types)
            limit = self.params.max_iocs_to_return

            ioc_category = entity_type_map.get(entity_type)

            if entity_type == EntityTypes.THREATACTOR:
                try:
                    threat_actor_id = get_threat_actor_id_by_origin(
                        self.api_client.get_threat_actor(entity_identifier)
                    )
                    if not threat_actor_id:
                        self.logger.info(
                            f"No Threat Actor with {entity_identifier} name were found "
                            f"in {INTEGRATION_DISPLAY_NAME}."
                        )
                        self.not_found_entities.append(entity_identifier)
                        continue

                    identifier = threat_actor_id
                except GoogleThreatIntelligenceExceptions as e:
                    self.logger.info(
                        f"Failed to fetch Threat Actor with {entity_identifier} name "
                        f": {e}"
                    )
                    self.not_found_entities.append(entity_identifier)
                    continue

            entity_results = {}
            for ioc_type in ioc_types:
                if ioc_type not in RELATIONSHIP_MAP.get(ioc_category, {}):
                    continue

                relationship_level = 1
                related_iocs = []

                while len(related_iocs) < limit:
                    relationship_key = (
                        f"{ioc_type}_{relationship_level}"
                        if relationship_level > 1
                        else ioc_type
                    )
                    relationship = RELATIONSHIP_MAP[ioc_category].get(
                        relationship_key, None
                    )
                    if not relationship:
                        break

                    try:
                        new_iocs = self.api_client.get_related_iocs(
                            ioc_category,
                            identifier,
                            relationship,
                            limit - len(related_iocs),
                        )
                        related_iocs.extend(new_iocs)
                        relationship_level += 1
                    except GoogleThreatIntelligencePermissionException as e:
                        log_type = (
                            "Hashes" if ioc_type.lower() == "Hash" else f"{ioc_type}s"
                        )
                        self.logger.info(
                            f"Permission denied to get {log_type} for "
                            f"{entity_identifier}: {e}"
                        )
                        relationship_level += 1

                    except GoogleThreatIntelligenceExceptions as e:
                        log_type = (
                            "Hashes" if ioc_type.lower() == "Hash" else f"{ioc_type}s"
                        )
                        self.logger.info(
                            f"Failed to fetch related {log_type} for "
                            f"{entity_identifier}: {e}"
                        )
                        break

                if related_iocs:
                    if ioc_type == "URL":
                        entity_results[ioc_type] = [ioc.url for ioc in related_iocs]
                    elif (
                        ioc_type == "Domain" and entity_type == EntityTypes.ADDRESS
                    ) or ioc_type == "IP":
                        entity_results[ioc_type] = [
                            ioc.id.replace(identifier, "") for ioc in related_iocs
                        ]
                    else:
                        entity_results[ioc_type] = [ioc.id for ioc in related_iocs]

            if entity_results:
                self.json_results[entity_identifier] = entity_results
                self.found_entities.append(entity_identifier)
            else:
                self.not_found_entities.append(entity_identifier)

        if self.found_entities:
            self.json_results = convert_dict_to_json_result_dict(self.json_results)
            self.output_message = (
                f"Successfully returned related IOCs for the following entities "
                f"in {INTEGRATION_DISPLAY_NAME}: {', '.join(self.found_entities)}.\n"
            )
            if self.not_found_entities:
                self.output_message += (
                    f"No related IOCs were found for the following entities in server:"
                    f" {', '.join(self.not_found_entities)}."
                )
        else:
            self.result_value = False
            self.output_message = (
                "No related IOCs were found for the provided entities."
            )


def main() -> None:
    GetRelatedIOCs(GET_RELATED_IOCS_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
