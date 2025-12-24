from __future__ import annotations

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    convert_dict_to_json_result_dict,
    convert_unixtime_to_datetime,
    output_handler,
    unix_now,
)
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.transformation import construct_csv

from ..core.constants import (
    ENRICH_IP_SCRIPT_NAME,
    ENRICH_TABLE_NAME,
    INTEGRATION_NAME,
)
from ..core.StairwellManager import StairwellManager
from ..core.utils import get_entity_original_identifier


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_IP_SCRIPT_NAME
    logger = siemplify.LOGGER
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="API Root", is_mandatory=True
    )
    api_key = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="API Key", is_mandatory=True
    )
    org_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Organization ID", is_mandatory=False
    )
    user_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="User ID", is_mandatory=False
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""
    successful_entities, failed_entities, json_results = [], [], {}
    suitable_entities = [
        entity for entity in siemplify.target_entities if entity.entity_type == EntityTypes.ADDRESS
    ]

    try:
        manager = StairwellManager(
            api_key=api_key, org_id=org_id, user_id=user_id, logger=logger, api_root=api_root
        )

        for entity in suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)

            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline "
                    f"({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) "
                    f"has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            siemplify.LOGGER.info(f"Started processing entity: {entity_identifier}")
            try:
                entity_report = manager.get_ip(entity_identifier)
                entity.additional_properties.update(entity_report.to_enrichment())
                entity.is_enriched = True
                entity.is_suspicious = manager.parser.is_entity_suspicious(entity_report)
                if entity.is_suspicious:
                    siemplify.add_entity_insight(
                        entity,
                        entity_report.to_insight(),
                        triggered_by=INTEGRATION_NAME,
                    )

                json_results[entity.identifier] = entity_report.to_json()
                siemplify.result.add_data_table(
                    title=ENRICH_TABLE_NAME.format(entity_identifier),
                    data_table=construct_csv([entity_report.to_csv()]),
                )
                successful_entities.append(entity)
            except Exception as e:
                failed_entities.append(entity_identifier)
                siemplify.LOGGER.error(f"An error occurred on entity {entity_identifier}")
                siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(f"Finished processing entity {entity_identifier}")

        if successful_entities:
            entity_identifiers = [
                get_entity_original_identifier(entity) for entity in successful_entities
            ]
            output_message += f"Successfully enriched IPs: \n{', '.join(entity_identifiers)}\n"
            siemplify.update_entities(successful_entities)

            if failed_entities:
                output_message += f"Failed processing entities:\n{', '.join(failed_entities)}\n"
        else:
            output_message = "No entities were enriched."
            result_value = False

        if json_results:
            siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {ENRICH_IP_SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = f"An error occurred while running action: {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
