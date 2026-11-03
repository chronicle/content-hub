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
from soar_sdk.SiemplifyUtils import (
    output_handler,
    convert_dict_to_json_result_dict,
    add_prefix_to_dict,
)
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from TIPCommon.extraction import extract_configuration_param
from TIPCommon.transformation import construct_csv

from ..core.constants import LOGIN_API_ROOT_DEFAULT, PROVIDER_NAME, ENRICH_ENTITIES_SCRIPT_NAME
from ..core.MicrosoftDefenderATPManager import (
    MicrosoftDefenderATPManager,
    MicrosoftDefenderATPError,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_ENTITIES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    login_api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Login API Root",
        default_value=LOGIN_API_ROOT_DEFAULT,
        is_mandatory=True,
    )

    api_root = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Api Root", input_type=str
    )

    client_id = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Client ID", input_type=str
    )

    client_secret = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Client Secret",
        input_type=str,
    )

    tenant_id = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Azure Active Directory ID",
        input_type=str,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=False,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    json_result = {}
    failed_entities = []
    missing_entities = []
    enriched_entities = []

    try:
        microsoft_defender_atp = MicrosoftDefenderATPManager(
            client_id=client_id,
            client_secret=client_secret,
            tenant_id=tenant_id,
            resource=api_root,
            login_api_root=login_api_root,
            verify_ssl=verify_ssl,
        )

        for entity in siemplify.target_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            if entity.entity_type in [EntityTypes.HOSTNAME, EntityTypes.ADDRESS]:
                if entity.entity_type == EntityTypes.HOSTNAME:
                    machines = microsoft_defender_atp.get_machines_by_name(
                        starts_with_name=entity.identifier
                    )
                else:
                    machines = microsoft_defender_atp.get_machines(ip=entity.identifier)

                if machines:
                    found_machine = machines[-1]

                    enrichment_data = add_prefix_to_dict(
                        found_machine.to_enrichment_data(), "Defender ATP"
                    )
                    entity.additional_properties.update(enrichment_data)
                    entity.is_enriched = True

                    enriched_entities.append(entity)

                    json_result[entity.identifier] = found_machine.to_json()
                    siemplify.result.add_entity_json(
                        entity_identifier=entity.identifier,
                        json_data=found_machine.to_json(),
                    )

                    siemplify.result.add_entity_table(
                        entity_identifier=entity.identifier,
                        data_table=construct_csv([found_machine.to_table()]),
                    )
                else:
                    missing_entities.append(entity)
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} was not enriched because nothing was found"
                    )

            elif entity.entity_type == EntityTypes.FILEHASH:
                try:
                    file_data = microsoft_defender_atp.get_file(entity.identifier)
                    enrichment_data = add_prefix_to_dict(
                        file_data.to_enrichment_data(), "Defender ATP"
                    )
                    entity.additional_properties.update(enrichment_data)
                    entity.is_enriched = True

                    enriched_entities.append(entity)

                    json_result[entity.identifier] = file_data.to_json()
                    siemplify.result.add_entity_json(
                        entity_identifier=entity.identifier,
                        json_data=file_data.to_json(),
                    )

                    siemplify.result.add_entity_table(
                        entity_identifier=entity.identifier,
                        data_table=construct_csv([file_data.to_table()]),
                    )
                except MicrosoftDefenderATPError as e:
                    siemplify.LOGGER.error(e)
                    siemplify.LOGGER.exception(e)
                    failed_entities.append(entity)

            else:
                siemplify.LOGGER.info(
                    f"Entity {entity.identifier} is of unsupported type, skipping..."
                )

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

        output_messages = [
            f"{len(enriched_entities)} entities enriched",
            f"{len(missing_entities)} entities missed",
            f"{len(failed_entities)} entities failed",
        ]

        if enriched_entities:
            siemplify.update_entities(enriched_entities)

            output_messages.append(
                f"Enriched Entities: {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string( [entity.identifier for entity in enriched_entities] )}"
            )

            output_messages.append(
                f"Missing Entities: {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string( [entity.identifier for entity in missing_entities] )}"
            )

            output_messages.append(
                f"Failed Entities: {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string( [entity.identifier for entity in missing_entities] )}"
            )

            result = "true"
        else:
            output_messages.append("No entities were enriched")
            result = "false"
            siemplify.LOGGER.warn("No entities were enriched")

        status = EXECUTION_STATE_COMPLETED
        output_message = "\n".join(output_messages)

    except MicrosoftDefenderATPError as e:
        output_message = f"Action didn't completed due to error: {e}"
        result = "false"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_result))
    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
