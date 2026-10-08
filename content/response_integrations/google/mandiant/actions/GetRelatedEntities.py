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
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from mandiant.core.MandiantManager import MandiantManager
from mandiant.core.constants import (
    INTEGRATION_NAME,
    GET_RELATED_ENTITIES_SCRIPT_NAME,
    MAX_SEVERITY_SCORE,
    DEFAULT_LIMIT,
    MALWARE_TYPE,
    THREAT_ACTOR_TYPE,
    IOC_MAPPING,
    RELATED_ENTITIES_DICT,
    INDICATOR_TYPE_MAPPING,
)
from mandiant.core.UtilsManager import get_entity_original_identifier, validate_positive_integer
import copy


SUPPORTED_ENTITY_TYPES = [
    EntityTypes.ADDRESS,
    EntityTypes.HOSTNAME,
    EntityTypes.FILEHASH,
    EntityTypes.URL,
    EntityTypes.THREATACTOR,
]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_RELATED_ENTITIES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

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
        param_name="Lowest Severity Score",
        default_value=50,
        print_value=True,
        input_type=int,
        is_mandatory=True,
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max IOCs To Return",
        default_value=DEFAULT_LIMIT,
        print_value=True,
        input_type=int,
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
    successful_entities, failed_entities = [], []
    json_result = {}

    try:
        validate_positive_integer(
            number=severity_score,
            err_msg="Lowest Severity Score parameter should be positive",
        )

        validate_positive_integer(
            number=limit, err_msg="Max IOCs To Return parameter should be positive"
        )

        if severity_score > MAX_SEVERITY_SCORE:
            raise Exception(
                f"Lowest Severity Score parameter should be no more than maximum value: {MAX_SEVERITY_SCORE}"
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

            try:
                related_indicators = []
                siemplify.LOGGER.info(f"Started processing entity: {entity_identifier}")
                if entity.entity_type == EntityTypes.THREATACTOR:
                    actor = manager.get_actor_details(
                        entity_identifier=entity_identifier
                    )
                    if actor:
                        related_indicators = manager.get_threat_actor_indicators(
                            identifier=actor.id,
                            limit=limit,
                            lowest_severity=severity_score,
                        )
                    else:
                        failed_entities.append(entity)
                else:
                    indicator_types = IOC_MAPPING.get(entity.entity_type)
                    details = manager.get_indicator_details(
                        entity_identifier=entity_identifier
                    )
                    if details:
                        indicator = next(
                            (
                                ind
                                for ind in details
                                if ind.type in indicator_types
                                and ind.value == entity_identifier
                            ),
                            None,
                        )
                        if indicator:
                            for attribute in indicator.attributed_associations:
                                if attribute.get("type") == MALWARE_TYPE:
                                    related_indicators = manager.get_malware_indicators(
                                        identifier=attribute.get("id"),
                                        limit=limit,
                                        lowest_severity=severity_score,
                                    )
                                if attribute.get("type") == THREAT_ACTOR_TYPE:
                                    related_indicators.extend(
                                        manager.get_threat_actor_indicators(
                                            identifier=attribute.get("id"),
                                            limit=limit,
                                            lowest_severity=severity_score,
                                        )
                                    )
                        else:
                            failed_entities.append(entity)
                    else:
                        failed_entities.append(entity)

                if related_indicators:
                    successful_entities.append(entity)
                    result_dict = copy.deepcopy(RELATED_ENTITIES_DICT)
                    ioc_types = set(
                        INDICATOR_TYPE_MAPPING.get(ind.type)
                        for ind in related_indicators
                    )
                    result_dict.update(
                        {
                            type: [
                                item.value
                                for item in related_indicators
                                if INDICATOR_TYPE_MAPPING.get(item.type) == type
                            ]
                            for type in ioc_types
                        }
                    )
                    json_result[entity_identifier] = result_dict
                else:
                    failed_entities.append(entity)

                siemplify.LOGGER.info(f"Finish processing entity: {entity_identifier}")
            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity_identifier}."
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message += (
                f"Successfully returned related indicators for the following entities using "
                f"information from {INTEGRATION_NAME}: "
                f"{', '.join([get_entity_original_identifier(entity) for entity in successful_entities])}\n\n"
            )

            if failed_entities:
                output_message += (
                    f"No related indicators were found for the following entities using information"
                    f" {INTEGRATION_NAME}: "
                    f"{', '.join([get_entity_original_identifier(entity) for entity in set(failed_entities)])}\n"
                )
        else:
            output_message = "No related indicators were found."
            result_value = False

        if json_result:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_result)
            )

    except Exception as e:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {GET_RELATED_ENTITIES_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
