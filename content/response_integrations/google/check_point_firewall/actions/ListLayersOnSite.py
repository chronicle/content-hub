from __future__ import annotations
from ..core.CheckpointManager import CheckpointManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import (
    INTEGRATION_NAME,
    LIST_LAYERS_ON_SITE_SCRIPT_NAME,
    ACCESS_CONTROL_LAYERS_CSV_NAME,
    THREAT_PREVENTION_CONTROL_LAYERS_CSV_NAME,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_LAYERS_ON_SITE_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATION:
    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Server Address",
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
    domain_name = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Domain",
        is_mandatory=False,
        default_value="",
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Layers To Return",
        input_type=int,
        default_value=50,
        print_value=True,
    )

    output_message = ""
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = CheckpointManager(
            server_address=server_address,
            username=username,
            password=password,
            domain=domain_name,
            verify_ssl=verify_ssl,
        )

        # Get Access and Threat layers
        access_layers = manager.get_access_layers(limit=limit)
        threat_layers = manager.get_threat_layers(limit=limit)

        # Add data to tables
        if access_layers:
            siemplify.result.add_data_table(
                title=ACCESS_CONTROL_LAYERS_CSV_NAME,
                data_table=construct_csv(
                    [access_layer.to_csv() for access_layer in access_layers]
                ),
            )
        if threat_layers:
            siemplify.result.add_data_table(
                title=THREAT_PREVENTION_CONTROL_LAYERS_CSV_NAME,
                data_table=construct_csv(
                    [threat_layer.to_csv() for threat_layer in threat_layers]
                ),
            )

        # Combine 2 responses and add json result
        siemplify.result.add_result_json(
            [access_layer.to_json() for access_layer in access_layers + threat_layers]
        )

        # Set output success message
        output_message = (
            "Successfully listed available Access Control and Threat Prevention layers."
        )
        manager.log_out()

    except Exception as err:
        output_message = f"No layers were found. Reason: {err}"
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
