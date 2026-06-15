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
from ..core.McAfeeMvisionEPOV2Manager import McAfeeMvisionEPOV2Manager
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, construct_csv
from ..core.constants import ENRICH_ENDPOINT_SCRIPT_NAME, INTEGRATION_NAME, ENRICHMENT_PREFIX
from ..core.exceptions import DeviceNotFoundException
from soar_sdk.SiemplifyDataModel import EntityTypes


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_ENDPOINT_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )

    iam_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="IAM Root",
        is_mandatory=True,
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
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
    )

    scopes = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Scopes",
        is_mandatory=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    enriched_entities = []
    enriched_entity_identifiers = []
    output_message = ""
    json_results = {}
    missing_entities = []
    failed_entities = []
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.ADDRESS
        or entity.entity_type == EntityTypes.HOSTNAME
    ]
    try:
        siemplify.LOGGER.info("Connecting to McAfee Mvision ePO V2.")
        manager = McAfeeMvisionEPOV2Manager(
            api_root,
            iam_root,
            client_id,
            client_secret,
            api_key,
            scopes,
            verify_ssl,
            siemplify.LOGGER,
        )
        siemplify.LOGGER.info("Successfully connected to McAfee Mvision ePO V2.")

        devices = []

        for entity in suitable_entities:
            try:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

                device = manager.find_entity_or_fail(
                    entity.identifier,
                    is_host=entity.entity_type == EntityTypes.HOSTNAME,
                )
                devices.append(device)

                siemplify.LOGGER.info(
                    f"Found device {device.device_id} for entity {entity.identifier}."
                )

                json_results[entity.identifier] = device.to_json()
                enriched_entity_identifiers.append(entity.identifier)
                enriched_entities.append(entity)
                entity.additional_properties.update(
                    device.to_enrichment_data(ENRICHMENT_PREFIX)
                )
                entity.is_enriched = True

                siemplify.add_entity_insight(entity, device.to_insight())

            except DeviceNotFoundException:
                missing_entities.append(entity.identifier)
                siemplify.LOGGER.error(
                    f"No device was found for entity: {entity.identifier}"
                )

            except Exception as e:
                failed_entities.append(entity.identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(f"Finished processing entity: {entity.identifier}")

        if devices:
            siemplify.result.add_data_table(
                title="Devices",
                data_table=construct_csv(
                    [device.to_table_data() for device in devices]
                ),
            )

        if enriched_entities:
            siemplify.update_entities(enriched_entities)
            output_message += ("Successfully enriched the following endpoints from "
                               "McAfee Mvision ePO V2: \n{}").format(
                "\n".join(enriched_entity_identifiers)
            )

        else:
            siemplify.LOGGER.info("\n No entities were enriched.")
            output_message = "No entities were enriched."
            result_value = False

        if missing_entities:
            output_message += ("\n\nAction was not able to find matching McAfee "
                               "Mvision ePO V2 devices for the following "
                               "endpoints: \n{}").format(
                "\n".join(missing_entities)
            )

        if failed_entities:
            output_message += ("\n\nAction was not able to enrich the following "
                               "endpoints from McAfee Mvision ePO V2: \n{}\n").format(
                "\n".join(failed_entities)
            )

    except Exception as e:
        output_message = (
            f"Error executing action '{ENRICH_ENDPOINT_SCRIPT_NAME}'. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  "
        f"result_value: {result_value}\n  "
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
