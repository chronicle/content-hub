from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SCCMManager import SCCMManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import INTEGRATION_NAME, GET_LOGIN_HISTORY_ACTION
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

ENTITY_TABLE_HEADER = "MS SCCM login history for {}"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_LOGIN_HISTORY_ACTION
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Server Address",
        is_mandatory=True,
    )
    domain = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Domain",
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )

    max_records_to_return = extract_action_param(
        siemplify,
        param_name="Number of Records to Return",
        is_mandatory=True,
        input_type=int,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""

    try:
        sccm = SCCMManager(server_address, domain, username, password)
        successful_entities = []
        failed_entities = []
        json_results = {}

        for entity in siemplify.target_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

            if entity.entity_type == EntityTypes.USER:
                login_history = sccm.get_login_history(
                    entity.identifier, max_records_to_return
                )

                if login_history:
                    json_results[entity.identifier] = login_history
                    successful_entities.append(entity.identifier)
                    # Add csv table
                    siemplify.result.add_entity_table(
                        ENTITY_TABLE_HEADER.format(entity.identifier),
                        construct_csv(login_history),
                    )
                else:
                    failed_entities.append(entity.identifier)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

        if successful_entities:
            output_message = (
                "Found SCCM information on the following entities:\n"
                + "\n".join(successful_entities)
            )
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

        if failed_entities:
            output_message += (
                "\nSCCM data for the following entities was not found:\n"
                + "\n".join(failed_entities)
            )

        if not successful_entities:
            output_message = "No results were found."
            result_value = False

    except Exception as e:
        output_message = (
            f"Failed to connect to the Microsoft SCCM instance! The reason is {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"Status: {status}, Result Value: {result_value}, Output Message: {output_message}"
    )

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
