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
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import construct_csv, string_to_multi_value

from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager
from crowd_strike_falcon.core.constants import (
    API_ROOT_DEFAULT,
    CID_ERROR,
    ENTITIES_MAPPER,
    INTEGRATION_NAME,
    LIST_HOST_VULNERABILITIES_SCRIPT_NAME,
    SEVERITY_POSSIBLE_VALUES,
)
from crowd_strike_falcon.core.datamodels import VulnerabilityList
from crowd_strike_falcon.core.exceptions import CrowdStrikeFalconValidatorException, InvalidCidError
from crowd_strike_falcon.core.utils import (
    MockEntity,
    get_entity_original_identifier,
    validate_device_id,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_HOST_VULNERABILITIES_SCRIPT_NAME
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    successful_entities, failed_entities, json_results = [], [], {}
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in ENTITIES_MAPPER
    ]

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    device_id_param = extract_action_param(
        siemplify,
        param_name="Device ID",
        print_value=True,
    )
    device_ids = string_to_multi_value(device_id_param)
    for device_id in device_ids:
        suitable_entities.append(MockEntity(device_id, "DEVICE_ID"))

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        default_value=API_ROOT_DEFAULT,
    )
    client_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client API ID"
    )
    client_secret = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client API Secret"
    )
    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
    )

    limit = extract_action_param(
        siemplify,
        param_name="Max Vulnerabilities To Return",
        input_type=int,
        print_value=True,
    )
    create_insight = extract_action_param(
        siemplify,
        param_name="Create Insight",
        default_value=True,
        print_value=True,
        input_type=bool,
    )
    severity = extract_action_param(
        siemplify, param_name="Severity Filter", print_value=True
    )
    severity = string_to_multi_value((severity or "").upper())
    integration_cid = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Customer ID",
        print_value=True
    )
    action_cid = extract_action_param(
        siemplify,
        param_name="Customer ID",
        print_value=True,
    )
    customer_id = action_cid or integration_cid

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        validate_device_id(device_id_param)
        if not all(item in SEVERITY_POSSIBLE_VALUES for item in severity):
            raise CrowdStrikeFalconValidatorException(
                f"Invalid value provided in the 'Severity Filter parameter. Possible values: "
                f"{', '.join(SEVERITY_POSSIBLE_VALUES)}'"
            )

        manager = CrowdStrikeManager(
            client_id=client_id,
            client_secret=client_secret,
            use_ssl=use_ssl,
            api_root=api_root,
            force_check_connectivity=True,
            customer_id=customer_id,
        )
        seen_devices = {}
        for entity in suitable_entities:
            remediations, remediation_ids = {}, []
            entity_identifier = get_entity_original_identifier(entity)
            try:
                if entity.entity_type == "DEVICE_ID":
                    device_info = manager.get_devices(devices_ids=[entity_identifier])
                    device_ids = [entity_identifier] if device_info else []
                else:
                    request_filter = {
                        key: entity_identifier
                        for key in ENTITIES_MAPPER[entity.entity_type]
                    }
                    request_filter["cid"] = customer_id
                    device_ids = manager.search_device_ids(**request_filter)

                if not device_ids:
                    siemplify.LOGGER.info(
                        f"No device found for entity {entity_identifier}. Skipping."
                    )
                    failed_entities.append(entity_identifier)
                    continue

                if device_ids[0] in seen_devices:
                    siemplify.LOGGER.info(
                        f"Identifier '{entity_identifier}' maps to device ID '{device_ids[0]}', which is already "
                        f"associated with entity '{seen_devices[device_ids[0]]}'. Skipping duplication."
                    )
                    continue

                seen_devices[device_ids[0]] = entity_identifier

                vulnerability_ids, total = manager.get_vulnerability_ids(
                    cid=customer_id, aid=device_ids[0], severity=severity, limit=limit
                )

                if not vulnerability_ids:
                    siemplify.LOGGER.info(
                        f"No Vulnerability ids found for entity {entity_identifier}. Skipping."
                    )
                    failed_entities.append(entity_identifier)
                    continue

                vulnerabilities = manager.get_vulnerabilities(vulnerability_ids)
                for vulnerability in vulnerabilities:
                    remediation_ids.extend(vulnerability.ids)

                if remediation_ids:
                    siemplify.LOGGER.info(
                        f"There are {len(remediation_ids)} remediation ids for entity "
                        f"{entity_identifier}."
                    )
                    remediations = manager.get_remediation_details(
                        ids=set(remediation_ids)
                    )
                vulnerability_list = VulnerabilityList(
                    vulnerabilities, remediations, total
                )
                json_results[entity_identifier] = vulnerability_list.to_json()

                siemplify.result.add_data_table(
                    f"{entity_identifier}",
                    construct_csv(
                        [
                            vulnerability.to_csv()
                            for vulnerability in vulnerability_list.vulnerabilities
                        ]
                    ),
                )
                if create_insight and entity.entity_type != "DEVICE_ID":
                    siemplify.add_entity_insight(
                        entity, vulnerability_list.to_insight()
                    )
                successful_entities.append(entity_identifier)

            except Exception as e:
                if CID_ERROR in str(e).lower():
                    raise InvalidCidError(
                        "Incorrect Customer ID specified."
                    ) from e
                failed_entities.append(entity_identifier)
                siemplify.LOGGER.error(
                    f"An error occurred for entity: {entity_identifier}"
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message = (
                f"Successfully retrieved vulnerabilities for the following hosts: "
                f'{", ".join(successful_entities)}\n'
            )

            if failed_entities:
                output_message += (
                    f"No vulnerabilities were found for the following hosts: "
                    f'{", ".join(failed_entities)}\n'
                )
        else:
            result_value = False
            output_message = "No vulnerabilities were found."

        if json_results:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

    except Exception as e:
        output_message = f"Error executing action '{LIST_HOST_VULNERABILITIES_SCRIPT_NAME}'. Reason: {e}"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
