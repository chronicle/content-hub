from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED, EXECUTION_STATE_COMPLETED
from ..core.CyberArkPamManager import CyberArkPamManager
from TIPCommon import extract_configuration_param
from ..core.constants import INTEGRATION_NAME

SCRIPT_NAME = "Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    ca_certificate = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="CA Certificate"
    )
    client_certificate = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client Certificate"
    )
    client_certificate_passphrase = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Certificate Passphrase",
        remove_whitespaces=False,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        siemplify.LOGGER.info(f"Connecting to {INTEGRATION_NAME}.")
        CyberArkPamManager(
            api_root=api_root,
            username=username,
            password=password,
            siemplify=siemplify,
            verify_ssl=verify_ssl,
            ca_certificate=ca_certificate,
            client_certificate=client_certificate,
            client_certificate_passphrase=client_certificate_passphrase,
        )

        log_message = (f"Successfully connected to the {INTEGRATION_NAME} "
                       f"installation with the provided connection parameters!")
        siemplify.LOGGER.info(log_message)
        output_message = log_message
        result_value = "true"
        status = EXECUTION_STATE_COMPLETED

    except Exception as e:
        log_message = (
            f"Failed to connect to the {INTEGRATION_NAME} installation! Error is {e}"
        )
        siemplify.LOGGER.error(log_message)
        siemplify.LOGGER.exception(e)
        output_message = log_message
        result_value = "false"
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
