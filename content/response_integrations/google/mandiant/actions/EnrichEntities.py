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
from typing import List, Optional, Union
from urllib.parse import urljoin, quote

from mandiant.core.MandiantManager import MandiantManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes, DomainEntityInfo
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    flat_dict_to_csv,
)
from mandiant.core.UtilsManager import get_entity_original_identifier, validate_positive_integer
from mandiant.core.constants import (
    INTEGRATION_NAME,
    ENRICH_ENTITIES_SCRIPT_NAME,
    MAX_SEVERITY_SCORE,
    INDICATOR_URL,
    ACTOR_URL,
    VULNERABILITY_URL,
    IOC_MAPPING,
    INVALID_ENTITIES,
)
from mandiant.core.datamodels import Vulnerability, ThreatActor, Indicator

SUPPORTED_ENTITY_TYPES = [
    EntityTypes.ADDRESS,
    EntityTypes.HOSTNAME,
    EntityTypes.FILEHASH,
    EntityTypes.CVE,
    EntityTypes.URL,
    EntityTypes.THREATACTOR,
]
INDICATOR_TYPES = [
    EntityTypes.ADDRESS,
    EntityTypes.HOSTNAME,
    EntityTypes.FILEHASH,
    EntityTypes.URL,
]
ACTOR_TYPES = [EntityTypes.THREATACTOR]
VULNERABILITY_TYPES = [EntityTypes.CVE]


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_ENTITIES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    ui_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="UI Root",
        is_mandatory=True,
        print_value=True,
    )
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    severity_score = extract_action_param(
        siemplify,
        param_name="Severity Score Threshold",
        default_value=50,
        print_value=True,
        input_type=int,
    )
    create_insight = extract_action_param(
        siemplify, param_name="Create Insight", print_value=True, input_type=bool
    )
    only_suspicious_insight = extract_action_param(
        siemplify,
        param_name="Only Suspicious Entity Insight",
        print_value=True,
        input_type=bool,
    )

    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_entities: List[DomainEntityInfo] = []
    failed_entities: List[DomainEntityInfo] = []
    json_result = {}
    invalid_entities: list[str] = INVALID_ENTITIES

    try:
        validate_positive_integer(
            number=severity_score,
            err_msg="Severity Score Threshold parameter should be positive",
        )
        if severity_score > MAX_SEVERITY_SCORE:
            raise Exception(
                f"Severity Score Threshold parameter should be less than maximum limit parameter: {MAX_SEVERITY_SCORE}"
            )

        manager = MandiantManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
            force_check_connectivity=True,
        )

        for entity in suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)
            # This property can become True if entity.entity_type from INDICATOR_TYPES and the entity marked as
            # suspicious or when they are different types than INDICATOR_TYPES
            entity_can_have_insight = False

            try:
                siemplify.LOGGER.info(f"Started processing entity: {entity_identifier}")
                result: Optional[Union[Vulnerability, ThreatActor, Indicator]] = None
                if entity.entity_type in INDICATOR_TYPES:
                    if entity_identifier not in invalid_entities:
                        indicator_types = IOC_MAPPING.get(entity.entity_type)
                        results = manager.get_indicator_details(
                            entity_identifier=entity_identifier
                        )
                        result = next(
                            (
                                indicator
                                for indicator in results
                                if indicator.type in indicator_types
                                and (
                                    entity_identifier
                                    in indicator.associated_hashes_values
                                    or entity_identifier == indicator.value
                                )
                            ),
                            None,
                        )
                    else:
                        siemplify.LOGGER.info(
                            f"Skipping invalid entity: {entity_identifier}"
                        )
                    if result:
                        result.report_link = urljoin(
                            ui_root,
                            INDICATOR_URL.format(
                                type=result.type,
                                value=(
                                    quote(result.value, safe="")
                                    if entity.entity_type == EntityTypes.URL
                                    else result.value
                                ),
                            ),
                        )

                        if result.mscore >= severity_score:
                            entity.is_suspicious = True
                            entity_can_have_insight = True
                    else:
                        failed_entities.append(entity)
                        continue
                elif entity.entity_type in ACTOR_TYPES:
                    result = manager.get_actor_details(
                        entity_identifier=entity_identifier
                    )
                    result.report_link = urljoin(
                        ui_root, ACTOR_URL.format(id=result.id)
                    )
                    entity_can_have_insight = True
                elif entity.entity_type in VULNERABILITY_TYPES:
                    result = manager.get_vulnerability_details(
                        entity_identifier=entity_identifier.upper()
                    )
                    result.report_link = urljoin(
                        ui_root, VULNERABILITY_URL.format(id=result.id)
                    )
                    entity_can_have_insight = True

                if result:
                    json_result[entity_identifier] = result.to_json()

                    siemplify.LOGGER.info(f"Enriching entity {entity_identifier}")
                    entity.additional_properties.update(result.to_enrichment())
                    entity.is_enriched = True

                    if create_insight:
                        if not only_suspicious_insight:
                            siemplify.LOGGER.info(
                                f"Adding insight for entity {entity_identifier}"
                            )
                            siemplify.add_entity_insight(entity, result.to_insight())

                        if only_suspicious_insight and entity_can_have_insight:
                            # Creating insight for indicator types, vulnerabilities and threat actors
                            siemplify.LOGGER.info(
                                f"Adding insight for entity {entity_identifier}"
                            )
                            siemplify.add_entity_insight(entity, result.to_insight())

                    siemplify.result.add_entity_table(
                        entity_identifier, flat_dict_to_csv(result.to_table())
                    )

                    successful_entities.append(entity)
                    siemplify.LOGGER.info(
                        f"Finish processing entity: {entity_identifier}"
                    )
            except Exception as critical_error:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity_identifier}."
                )
                siemplify.LOGGER.exception(critical_error)

        if successful_entities:
            output_message += (
                f"Successfully enriched the following entities using information from "
                f"{INTEGRATION_NAME}: "
                f"{', '.join([get_entity_original_identifier(entity) for entity in successful_entities])}\n\n"
            )
            siemplify.update_entities(successful_entities)

            if failed_entities:
                output_message += (
                    f"Action wasn't able to enrich the following entities using information from"
                    f" {INTEGRATION_NAME}: "
                    f"{', '.join([get_entity_original_identifier(entity) for entity in failed_entities])}\n"
                )
        else:
            output_message = "None of the provided entities were enriched."
            result_value = False

        if json_result:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_result)
            )

    except Exception as critical_error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action {ENRICH_ENTITIES_SCRIPT_NAME}. Reason: {critical_error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(critical_error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
