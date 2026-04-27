from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.CBResponseManagerLoader import CBResponseManagerLoader
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

# =====================================
#             CONSTANTS               #
# =====================================
INTEGRATION_NAME = "CBResponse"
SCRIPT_NAME = "CBResponse - Process Free Query"
ENTITY_TABLE_HEADER = "Processes"


@output_handler
def main():
    siemplify = SiemplifyAction()
    status = EXECUTION_STATE_COMPLETED
    result_value = "true"
    siemplify.script_name = SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Root", input_type=str
    )
    api_key = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Key", input_type=str
    )
    version = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Version",
        input_type=float,
    )
    ca_certificate_file = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File",
        input_type=str,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        param_name="Verify SSL",
        provider_name=INTEGRATION_NAME,
        default_value=False,
        input_type=bool,
    )

    # INIT ACTION PARAMETERS:
    query = extract_action_param(
        siemplify,
        param_name="Query",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        # If no exception occur - then connection is successful
        manager = CBResponseManagerLoader.load_manager(
            version,
            api_root,
            api_key,
            siemplify.LOGGER,
            verify_ssl,
            ca_certificate_file,
        )
        processes = manager.process_free_query(query)

        if processes:
            siemplify.result.add_entity_table(
                ENTITY_TABLE_HEADER,
                construct_csv([process.to_csv() for process in processes]),
            )
            siemplify.result.add_result_json(
                [process.to_json() for process in processes]
            )

            output_message = f"Found {len(processes)} processes."
        else:
            output_message = "No processes were found."

        siemplify.LOGGER.info("Finished processing")
    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = "Some errors occurred. Please check log"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
