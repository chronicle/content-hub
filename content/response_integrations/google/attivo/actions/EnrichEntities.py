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
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.AttivoManager import AttivoManager
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    construct_csv,
    dict_to_flat,
)
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    ENRICH_ENTITIES_SCRIPT_NAME,
    DEFAULT_ENTITIES_LIMIT,
)


SUPPORTED_ENTITY_TYPES = [EntityTypes.HOSTNAME, EntityTypes.ADDRESS]
ENRICHMENT_PREFIX = "Attivo"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_ENTITIES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    include_threatpaths = extract_action_param(
        siemplify,
        param_name="Include ThreatPaths",
        default_value=True,
        print_value=True,
        input_type=bool,
    )
    include_vulnerabilities = extract_action_param(
        siemplify,
        param_name="Include Vulnerabilities",
        default_value=True,
        print_value=True,
        input_type=bool,
    )
    include_credentials = extract_action_param(
        siemplify,
        param_name="Include Credential Info",
        default_value=True,
        print_value=True,
        input_type=bool,
    )
    create_insights = extract_action_param(
        siemplify,
        param_name="Create Insights",
        default_value=True,
        print_value=True,
        input_type=bool,
    )
    threatpaths_limit = extract_action_param(
        siemplify,
        param_name="Max ThreatPaths To Return",
        input_type=int,
        print_value=True,
        default_value=DEFAULT_ENTITIES_LIMIT,
    )
    vulnerabilities_limit = extract_action_param(
        siemplify,
        param_name="Max Vulnerabilities To Return",
        input_type=int,
        print_value=True,
        default_value=DEFAULT_ENTITIES_LIMIT,
    )
    credentials_limit = extract_action_param(
        siemplify,
        param_name="Max Credentials To Return",
        input_type=int,
        print_value=True,
        default_value=DEFAULT_ENTITIES_LIMIT,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    successful_entities, failed_entities, json_results = [], [], {}
    result_value = True
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        if threatpaths_limit < 1:
            raise Exception('"Max ThreatPaths To Return" must be greater than 0.')
        if vulnerabilities_limit < 1:
            raise Exception('"Max Vulnerabilities To Return" must be greater than 0.')
        if credentials_limit < 1:
            raise Exception('"Max Credentials To Return" must be greater than 0.')

        manager = AttivoManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        for entity in suitable_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

            try:
                entity_info = manager.get_hostname_info(
                    identifier=entity.identifier,
                    is_hostname=(
                        True if entity.entity_type == EntityTypes.HOSTNAME else False
                    ),
                )

                if entity_info:
                    if include_threatpaths:
                        entity_info.threatpaths = manager.get_threatpaths(
                            hostname=entity_info.hostname, limit=threatpaths_limit
                        )
                    if include_vulnerabilities:
                        entity_info.vulnerabilities = manager.get_vulnerabilities(
                            hostname=entity_info.hostname, limit=vulnerabilities_limit
                        )
                    if include_credentials:
                        entity_info.creds = manager.get_credentials(
                            hostname=entity_info.hostname, limit=credentials_limit
                        )

                    entity.additional_properties.update(
                        entity_info.to_table(
                            include_threatpaths,
                            include_vulnerabilities,
                            include_credentials,
                            prefix=ENRICHMENT_PREFIX,
                        )
                    )
                    json_results[entity.identifier] = entity_info.as_json(
                        include_threatpaths,
                        include_vulnerabilities,
                        include_credentials,
                    )
                    entity.is_enriched = True
                    successful_entities.append(entity)
                    if create_insights:
                        siemplify.add_entity_insight(
                            entity,
                            entity_info.to_insight(
                                include_threatpaths,
                                include_vulnerabilities,
                                include_credentials,
                            ),
                        )
                    siemplify.result.add_entity_table(
                        entity.identifier, construct_csv([entity_info.to_csv()])
                    )
                    if include_threatpaths:
                        siemplify.result.add_entity_table(
                            f"{entity.identifier} ThreatPaths",
                            construct_csv(
                                [path.to_csv() for path in entity_info.threatpaths]
                            ),
                        )
                    if include_vulnerabilities:
                        siemplify.result.add_entity_table(
                            f"{entity.identifier} Vulnerabilities",
                            construct_csv(
                                [
                                    dict_to_flat({"Name": vuln})
                                    for vuln in entity_info.vulnerabilities
                                ]
                            ),
                        )
                    if include_credentials:
                        siemplify.result.add_entity_table(
                            f"{entity.identifier} Credentials",
                            construct_csv(
                                [cred.to_csv() for cred in entity_info.creds]
                            ),
                        )
                else:
                    failed_entities.append(entity.identifier)

            except Exception as e:
                failed_entities.append(entity.identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

        if successful_entities:
            output_message = (
                f"Successfully enriched the following entities using information from "
                f"{INTEGRATION_DISPLAY_NAME}: "
                f'{", ".join([entity.identifier for entity in successful_entities])}\n'
            )
            siemplify.update_entities(successful_entities)
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            if failed_entities:
                output_message += (
                    f"Action wasn't able to enrich the following entities using information from "
                    f'{INTEGRATION_DISPLAY_NAME}: {", ".join(failed_entities)}\n'
                )
        else:
            output_message = "None of the provided entities were enriched."
            result_value = False

    except Exception as e:
        output_message = (
            f'Error executing action "{ENRICH_ENTITIES_SCRIPT_NAME}". Reason: {e}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
