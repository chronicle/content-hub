from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.AlienVaultManagerLoader import AlienVaultManagerLoader
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    flat_dict_to_csv,
)
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED


INTEGRATION_NAME = "AlienVaultAnywhere"
SCRIPT_NAME = "Get Alarm Details"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    version = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Product Version",
        is_mandatory=True,
        default_value="V1",
    )
    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
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
    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        default_value=True,
        input_type=bool,
    )

    alarm_id = extract_action_param(
        siemplify,
        param_name="Alarm ID",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )

    if version == "V1":
        siemplify.end(
            "This action is not supported for AlienVault Anywhere V1 integration. Please use V2.",
            "false",
            EXECUTION_STATE_FAILED,
        )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    json_results = {}
    result_value = "true"
    status = EXECUTION_STATE_COMPLETED

    try:
        alienvault_manager = AlienVaultManagerLoader.load_manager(
            version=version,
            api_root=server_address,
            username=username,
            password=password,
            use_ssl=use_ssl,
            chronicle_soar=siemplify,
        )
        alarm = alienvault_manager.get_alarm_by_id(alarm_id)

        siemplify.result.add_data_table(
            f"Alarm {alarm_id} Details", flat_dict_to_csv(alarm.to_csv())
        )
        json_results = alarm.raw_data
        output_message = (
            f"Successfully returned Alien Vault Anywhere alarm {alarm_id} details"
        )

        alienvault_manager.session.close()

    except Exception as e:
        siemplify.LOGGER.error(
            f"Failed to get details about Alien Vault Anywhere alarm! Error is {e}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = (
            f"Failed to get details about Alien Vault Anywhere alarm! Error is {e}"
        )

    siemplify.result.add_result_json(json_results)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
