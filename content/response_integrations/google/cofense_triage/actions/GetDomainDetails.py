from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    convert_dict_to_json_result_dict,
    get_domain_from_entity,
    output_handler,
)

from TIPCommon.extraction import extract_configuration_param
from TIPCommon.transformation import construct_csv

from ..core.constants import INTEGRATION_NAME, GET_DOMAIN_DETAILS_ACTION
from ..core.CofenseTriageManager import CofenseTriageManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_DOMAIN_DETAILS_ACTION
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
    successful_entities = []
    failed_entities = []
    output_message = ""
    json_results = {}
    domain_table = []

    scope_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.URL
    ]

    try:
        cofensetriage_manager = CofenseTriageManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
        )
        for entity in scope_entities:
            siemplify.LOGGER.info(f"Started processing entity:{entity.identifier}")
            try:
                domain = get_domain_from_entity(entity)
                domain_object = cofensetriage_manager.get_domain_details(domain)

                if not domain_object.to_json():
                    siemplify.LOGGER.info(
                        f"No domain details were found for entity: {entity.identifier}"
                    )
                    failed_entities.append(entity)
                    continue

                successful_entities.append(entity)
                json_results[entity.identifier] = domain_object.to_json()
                domain_table.append(domain_object.to_table())
            except Exception as e:
                output_message += f"Unable to enrich entity: {entity.identifier} \n"
                failed_entities.append(entity)
                siemplify.LOGGER.error(f"Failed processing entity:{entity.identifier}")
                siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(f"Finished processing entity:{entity.identifier}")

    except Exception as e:
        output_message += (
            f"Error executing action {GET_DOMAIN_DETAILS_ACTION}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    if len(scope_entities) == len(failed_entities):
        output_message += "No information about the domains was found."
        result_value = False

    else:
        if successful_entities:
            output_message += ("Successfully returned details about "
                               "the following domains using {}: \n{}").format(
                INTEGRATION_NAME,
                "\n".join([entity.identifier for entity in successful_entities]),
            )
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            siemplify.result.add_entity_table(
                "Domain Details", construct_csv(domain_table)
            )
        if failed_entities:
            output_message += ("\nAction wasn't able to get details "
                               "about the following domains using {}:\n{}").format(
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
