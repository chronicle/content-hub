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
from mandiant.core.MandiantManager import MandiantManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    string_to_multi_value,
)
from mandiant.core.constants import ENRICH_IOCS_SCRIPT_NAME, INTEGRATION_NAME, INDICATOR_TYPE_MAPPING


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_IOCS_SCRIPT_NAME
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

    ioc_identifiers = string_to_multi_value(
        extract_action_param(
            siemplify, param_name="IOC Identifiers", print_value=True, is_mandatory=True
        )
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_entities, failed_entities = [], []
    json_result = {}

    try:
        manager = MandiantManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
            force_check_connectivity=True,
        )

        for ioc_identifier in ioc_identifiers:
            try:
                siemplify.LOGGER.info(f"Started processing entity: {ioc_identifier}")
                try:
                    siemplify.LOGGER.info(
                        f"Finding result for vulnerability with entity: {ioc_identifier}"
                    )
                    result = manager.get_vulnerability_details(
                        entity_identifier=ioc_identifier.upper()
                    )
                except Exception:
                    siemplify.LOGGER.error(
                        f"Failed find result for vulnerability with entity: {ioc_identifier}."
                    )
                    try:
                        siemplify.LOGGER.info(
                            f"Finding result for malware with entity: {ioc_identifier}"
                        )
                        result = manager.get_malware_details(identifier=ioc_identifier)
                    except Exception:
                        siemplify.LOGGER.error(
                            f"Failed find result for malware with entity: {ioc_identifier}."
                        )
                        try:
                            siemplify.LOGGER.info(
                                f"Finding result for threat actor with entity: {ioc_identifier}"
                            )
                            result = manager.get_actor_details(
                                entity_identifier=ioc_identifier
                            )
                        except Exception:
                            siemplify.LOGGER.error(
                                f"Failed find result for threat actor with entity: {ioc_identifier}."
                            )
                            results = manager.get_indicator_details(
                                entity_identifier=ioc_identifier
                            )
                            indicator_types = INDICATOR_TYPE_MAPPING.keys()
                            result = next(
                                (
                                    indicator
                                    for indicator in results
                                    if indicator.type in indicator_types
                                    and (
                                        ioc_identifier
                                        in indicator.associated_hashes_values
                                        or ioc_identifier.lower() == indicator.value
                                    )
                                ),
                                None,
                            )

                if not result:
                    failed_entities.append(ioc_identifier)
                    continue

                if isinstance(result, list):
                    for result_item in result:
                        if result_item.value == ioc_identifier:
                            # try to find exact match
                            result_item.set_report_link(ui_root)
                            json_result[ioc_identifier] = result_item.to_json()
                            break
                    else:
                        # if no exact match, take the first result
                        result[0].set_report_link(ui_root)
                        json_result[ioc_identifier] = result[0].to_json()
                else:
                    result.set_report_link(ui_root)
                    json_result[ioc_identifier] = result.to_json()

                successful_entities.append(ioc_identifier)
                siemplify.LOGGER.info(f"Finish processing entity: {ioc_identifier}")
            except Exception as e:
                failed_entities.append(ioc_identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {ioc_identifier}."
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message += (
                f"Successfully enriched the following IOCs using information from {INTEGRATION_NAME}: "
                f"{', '.join(successful_entities)}\n\n"
            )
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_result)
            )

            if failed_entities:
                output_message += (
                    f"Action wasn't able to enrich the following IOCs using information from "
                    f"{INTEGRATION_NAME}: {', '.join(failed_entities)}"
                )
        else:
            output_message = "No IOCs were enriched."
            result_value = False

    except Exception as critical_error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action {ENRICH_IOCS_SCRIPT_NAME}. Reason: {critical_error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(critical_error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}"
        f"\n  is_success: {result_value}"
        f"\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
