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
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv
from ..core.CBCloudManager import CBCloudManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from ..core.constants import (
    INTEGRATION_NAME,
    LIST_HOST_VULNERABILITIES_SCRIPT_NAME,
    SEVERITY_FILTER_MAPPING,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.utils import (
    get_entity_original_identifier,
    convert_comma_separated_to_list,
    convert_list_to_comma_string,
)


ENTITIES_MAPPER = {
    EntityTypes.ADDRESS: "query",
    EntityTypes.HOSTNAME: "starts_with_name",
}
DEFAULT_LIMIT = 3


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_HOST_VULNERABILITIES_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    org_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Organization Key",
        is_mandatory=True,
    )
    api_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API ID",
        is_mandatory=True,
    )
    api_secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Secret Key",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    # action parameters
    severity_filter = extract_action_param(
        siemplify, param_name="Severity Filter", print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Vulnerabilities To Return",
        input_type=int,
        print_value=True,
    )

    severities = [
        item.lower() for item in convert_comma_separated_to_list(severity_filter)
    ]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    successful_entities, failed_entities, json_results = [], [], {}
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in ENTITIES_MAPPER.keys()
    ]

    try:
        if limit is not None and limit < 1:
            raise Exception(
                f'Invalid value was provided for "Max Vulnerabilities To Return": {limit}. '
                f"Positive number should be provided."
            )

        if severities and set(severities) - set(SEVERITY_FILTER_MAPPING.keys()):
            raise Exception(
                f'Invalid value provided in the "Severity Filter" parameter. Possible values: '
                f"{convert_list_to_comma_string(list(SEVERITY_FILTER_MAPPING.keys()))}."
            )

        manager = CBCloudManager(
            api_root=api_root,
            org_key=org_key,
            api_id=api_id,
            api_secret_key=api_secret_key,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )

        for entity in suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)
            siemplify.LOGGER.info(f"Started processing entity: {entity_identifier}")

            try:
                siemplify.LOGGER.info(
                    f"Fetching device info for entity {entity_identifier}"
                )
                params = {
                    ENTITIES_MAPPER[entity.entity_type]: entity_identifier,
                    "limit": DEFAULT_LIMIT,
                }

                devices = manager.search_devices(**params)

                if not devices:
                    failed_entities.append(entity_identifier)
                    siemplify.LOGGER.info(
                        f"No devices were found for entity {entity_identifier}. Skipping."
                    )
                    siemplify.LOGGER.info(
                        f"Finished processing entity {entity_identifier}"
                    )
                    continue

                if len(devices) > 1:
                    siemplify.LOGGER.info(
                        f"Multiple matches found for entity {entity_identifier}, taking first match."
                    )

                # Take the first matching device already sorted by last_contact_time
                device = devices[-1]

                # Get vulnerability details
                details = manager.get_vulnerability_details(
                    device.id, severities, limit
                )

                if not details:
                    failed_entities.append(entity_identifier)
                    siemplify.LOGGER.info(
                        f"No vulnerabilities were found for entity {entity_identifier}."
                    )
                    siemplify.LOGGER.info(
                        f"Finished processing entity {entity_identifier}"
                    )
                    continue

                json_results[entity_identifier] = {
                    "statistics": get_statistics(details),
                    "details": [detail.to_json() for detail in details],
                }
                siemplify.result.add_entity_table(
                    entity_identifier,
                    construct_csv([detail.to_table() for detail in details]),
                )

                successful_entities.append(entity)
                siemplify.LOGGER.info(f"Finished processing entity {entity_identifier}")

            except Exception as e:
                failed_entities.append(entity_identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity_identifier}"
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            siemplify.update_entities(successful_entities)
            output_message = (
                f"Successfully retrieved vulnerabilities for the following hosts:\n "
                f"{convert_list_to_comma_string(successful_entities)}\n"
            )
        if failed_entities:
            output_message += (
                f"\nNo vulnerabilities were found for the following hosts:\n "
                f"{convert_list_to_comma_string(failed_entities)}"
            )

        if not successful_entities:
            result_value = False
            output_message = "No vulnerabilities were found."

    except Exception as e:
        result_value = False
        output_message = f"Error executing action {LIST_HOST_VULNERABILITIES_SCRIPT_NAME}. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


def get_statistics(details):
    critical, important, moderate, low = 0, 0, 0, 0

    for detail in details:
        if detail.severity == SEVERITY_FILTER_MAPPING.get("critical"):
            critical += 1
        if detail.severity == SEVERITY_FILTER_MAPPING.get("important"):
            important += 1
        if detail.severity == SEVERITY_FILTER_MAPPING.get("moderate"):
            moderate += 1
        if detail.severity == SEVERITY_FILTER_MAPPING.get("low"):
            low += 1

    return {
        "total": len(details),
        "severity": {
            "critical": critical,
            "important": important,
            "moderate": moderate,
            "low": low,
        },
    }


if __name__ == "__main__":
    main()
