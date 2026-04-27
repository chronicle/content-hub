from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.AlienVaultManagerLoader import AlienVaultManagerLoader
from TIPCommon import extract_configuration_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

INTEGRATION_NAME = "AlienVaultAnywhere"
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_FAILED
    connectivity_result = False

    try:
        alienvault_manager = AlienVaultManagerLoader.load_manager(
            version=version,
            api_root=server_address,
            username=username,
            password=password,
            use_ssl=use_ssl,
            chronicle_soar=siemplify,
        )
        alienvault_manager.test_connectivity()

        connectivity_result = True
        status = EXECUTION_STATE_COMPLETED
        output_message = "Connected successfully."

        alienvault_manager.session.close()

    except Exception as e:
        output_message = f"Failed to connect to the AlienVaultAnywhere! Error is {e}"
        siemplify.LOGGER.error(
            f"Connection to API failed, performing action {PING_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)

    siemplify.end(output_message, connectivity_result, status)


if __name__ == "__main__":
    main()
