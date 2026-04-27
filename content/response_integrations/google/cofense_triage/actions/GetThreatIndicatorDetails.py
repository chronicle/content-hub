from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler

from TIPCommon.extraction import extract_configuration_param
from TIPCommon.transformation import construct_csv

from ..core.constants import (
    GET_THREAT_INDICATOR_DETAILS_ACTION,
    INTEGRATION_NAME,
    THREAT_LEVELS,
)
from ..core.CofenseTriageManager import CofenseTriageManager
from ..core.UtilsManager import get_entity_original_identifier, is_valid_email


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_THREAT_INDICATOR_DETAILS_ACTION
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
        print_value=True,
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
        default_value=False,
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    json_results = {}
    entities_to_update = []
    failed_entities = []
    output_message = ""
    ti_details_table = []

    try:
        cofensetriage_manager = CofenseTriageManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
        )
        for entity in siemplify.target_entities:
            siemplify.LOGGER.info(f"Started processing entity:{entity.identifier}")
            try:
                entity_identifier = entity.identifier

                if entity.entity_type == EntityTypes.USER and is_valid_email(
                    get_entity_original_identifier(entity)
                ):
                    entity_identifier = (
                        f"From:{entity.identifier},To:{entity.identifier}"
                    )

                if entity.entity_type == EntityTypes.EMAILMESSAGE:
                    entity_identifier = f"Subject:{entity.identifier}"

                entity_object = cofensetriage_manager.get_threat_indicator_details(
                    entity_identifier
                )

                if not entity_object.to_json():
                    siemplify.LOGGER.info(
                        f"No threat indicators were found for entity: "
                        f"{entity.identifier}"
                    )
                    failed_entities.append(entity)
                    continue

                if entity_object.ti_threat_level in THREAT_LEVELS:
                    entity.is_suspicious = True

                json_results[entity.identifier] = entity_object.to_json()
                entities_to_update.append(entity)
                entity.is_enriched = True
                entity.additional_properties.update(entity_object.as_enrichment_data())
                ti_details_table.append(entity_object.to_table())

            except Exception as e:
                output_message += f"Unable to enrich entity: {entity.identifier} \n"
                failed_entities.append(entity)
                siemplify.LOGGER.error(f"Failed processing entity:{entity.identifier}")
                siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(f"Finished processing entity:{entity.identifier}")

    except Exception as e:
        output_message += (
            f"Error executing action {GET_THREAT_INDICATOR_DETAILS_ACTION}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    if len(siemplify.target_entities) == len(failed_entities):
        output_message += (
            "No threat indicator information about the entities was found."
        )
        result_value = False

    else:
        if entities_to_update:
            siemplify.update_entities(entities_to_update)
            output_message += ("Successfully returned threat indicator details "
                               "about the following entities using {}:\n{}").format(
                INTEGRATION_NAME,
                "\n".join([entity.identifier for entity in entities_to_update]),
            )
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            siemplify.result.add_entity_table(
                "Threat Indicator Table", construct_csv(ti_details_table)
            )

        if failed_entities:
            output_message += ("\nAction wasn't able to return threat indicator "
                               "details about the following entities "
                               "using {}:\n{}").format(
                INTEGRATION_NAME,
                "\n".join([entity.identifier for entity in failed_entities]),
            )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  "
        f"result_value: {result_value}\n  "
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
