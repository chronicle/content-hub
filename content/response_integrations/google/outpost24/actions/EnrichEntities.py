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
from TIPCommon import construct_csv, extract_action_param, extract_configuration_param

from ..core.constants import (
    ENRICH_ENTITIES_SCRIPT_NAME,
    ENRICHMENT_PREFIX,
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_NAME,
    SUPORTED_RISK_LEVELS,
)
from ..core.Outpost24Exceptions import DeviceNotFoundError
from ..core.Outpost24Manager import Outpost24Manager
from ..core.UtilsManager import load_csv_to_list

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


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
        print_value=False,
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
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result = True
    output_message = ""
    json_result = {}
    successful_entities = []
    failed_entities = []
    invalid_risk_levels = None
    try:
        create_insight = extract_action_param(
            siemplify,
            param_name="Create Insight",
            is_mandatory=False,
            print_value=True,
            default_value=True,
            input_type=bool,
        )
        risk_level_filter = extract_action_param(
            siemplify,
            param_name="Finding Risk Level Filter",
            default_value="Low, Medium, High, Critical, Recommendation, Initial",
            is_mandatory=False,
            print_value=True,
            input_type=str,
        )
        max_findings_to_return = extract_action_param(
            siemplify,
            param_name="Max Findings To Return",
            default_value="",
            is_mandatory=False,
            print_value=True,
            input_type=int,
        )
        return_finding_information = extract_action_param(
            siemplify,
            param_name="Return Finding Information",
            is_mandatory=False,
            print_value=True,
            default_value=True,
            input_type=bool,
        )
        finding_type = extract_action_param(
            siemplify,
            param_name="Finding Type",
            default_value="All",
            is_mandatory=False,
            print_value=True,
            input_type=str,
        )

        manager = Outpost24Manager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        manager.test_connectivity()

        if max_findings_to_return < 1:
            msg = (
                f'Given value of {max_findings_to_return} for parameter "Max Findings '
                'To Return" is non positive.'
            )
            raise Exception(
                msg
            )

        # check the risk level input
        if return_finding_information:
            if risk_level_filter is not None:
                risk_level_filter = load_csv_to_list(risk_level_filter, "Risk Levels")
                risk_level_filter = [risk.lower() for risk in risk_level_filter]
                invalid_risk_levels = list(
                    set(risk_level_filter) - set(SUPORTED_RISK_LEVELS)
                )
                invalid_risk_levels_message = ",".join(invalid_risk_levels)
                if invalid_risk_levels is not None:
                    msg = (
                        f"invalid risk level filter values provided: "
                        f"{invalid_risk_levels_message}. Possible values: "
                        f"Recommendation, Initial, Low, Medium, High, Critical."
                    )
                    raise Exception(
                        msg
                    )

        suitable_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        ]

        for entity in suitable_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            try:
                if entity.entity_type == EntityTypes.HOSTNAME:
                    entity_details = manager.get_device_information(
                        entity.identifier,
                        is_hostname=True,
                        risk_level_filter=risk_level_filter,
                        return_finding_information=return_finding_information,
                        finding_type=finding_type,
                        max_findings_to_return=max_findings_to_return,
                    )

                else:
                    entity_details = manager.get_device_information(
                        entity.identifier,
                        risk_level_filter=risk_level_filter,
                        return_finding_information=return_finding_information,
                        finding_type=finding_type,
                        max_findings_to_return=max_findings_to_return,
                    )

                if entity_details and entity_details.raw_data:
                    json_result[entity.identifier] = entity_details.to_json(
                        return_finding_information=return_finding_information
                    )
                    entity.additional_properties.update(
                        entity_details.to_enrichment_data(
                            prefix=ENRICHMENT_PREFIX,
                            return_finding_information=return_finding_information,
                        )
                    )
                    entity.is_enriched = True
                    successful_entities.append(entity)
                    siemplify.result.add_data_table(
                        entity.identifier,
                        data_table=construct_csv(entity_details.to_table()),
                    )
                    if (
                        return_finding_information
                        and entity_details.to_findings_table()
                    ):
                        siemplify.result.add_data_table(
                            f"Findings: {entity.identifier}",
                            data_table=construct_csv(
                                entity_details.to_findings_table()
                            ),
                        )

                    if create_insight:
                        siemplify.add_entity_insight(
                            entity,
                            entity_details.as_insight(
                                return_finding_information=return_finding_information
                            ),
                            triggered_by=INTEGRATION_DISPLAY_NAME,
                        )
                else:
                    failed_entities.append(entity)

            except DeviceNotFoundError as e:
                failed_entities.append(entity)
                siemplify.LOGGER.info(
                    f"Failed processing entity {entity.identifier}. Reason: {e}"
                )
                continue

            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.info(
                    f"Failed processing entity {entity.identifier}. Reason: {e}"
                )
                continue

        if successful_entities:
            output_message += (
                "Successfully enriched the following entities using {}: \n{}".format(
                    INTEGRATION_NAME,
                    "\n".join([entity.identifier for entity in successful_entities]),
                )
            )
            siemplify.update_entities(successful_entities)
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_result)
            )

        if failed_entities:
            output_message += (
                "\nAction wasn't able to enrich the following entities "
                "using {}: \n{}").format(
                INTEGRATION_NAME,
                "\n".join([entity.identifier for entity in failed_entities]),
            )

        if not successful_entities:
            result = False
            output_message = "None of the provided entities were enriched."

    except Exception as e:
        siemplify.LOGGER.exception(
            f"General error performing action {ENRICH_ENTITIES_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {ENRICH_ENTITIES_SCRIPT_NAME}. Reason: {e}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
