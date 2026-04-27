from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.IronportManagerAPI import IronportManagerAPI
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from ..core.IronportConstants import INTEGRATION_NAME, SCRIPT_PING
from ..core.IronportExceptions import (
    IronportManagerException,
    IronportAsyncOSConnectionException,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_PING

    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Server Address",
        print_value=True,
        input_type=str,
        is_mandatory=True,
    )

    async_os_port = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AsyncOS API Port",
        print_value=True,
        input_type=int,
        is_mandatory=True,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        print_value=False,
        input_type=str,
        is_mandatory=True,
    )

    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        print_value=False,
        input_type=str,
        is_mandatory=True,
    )

    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File - parsed into Base64 String",
    )

    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use SSL",
        print_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        print_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    try:
        siemplify.LOGGER.info("Checking AsyncOS manager's connectivity")
        IronportManagerAPI(
            server_address=server_address,
            port=async_os_port,
            username=username,
            password=password,
            ca_certificate=ca_certificate,
            use_ssl=use_ssl,
            verify_ssl=verify_ssl,
        )

        output_message = "Successfully connected to the IronPort server with the provided connection parameters!"
        siemplify.LOGGER.info(output_message)
        is_success = True
        status = EXECUTION_STATE_COMPLETED

    except IronportAsyncOSConnectionException as e:
        output_message = (
            f"Failed to connect to the IronPort AsyncOS REST API! Error is {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        is_success = False
        status = EXECUTION_STATE_FAILED

    except (IronportManagerException, Exception) as e:
        output_message = f"Something went wrong. Error is {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        is_success = False
        status = EXECUTION_STATE_FAILED

    siemplify.end(output_message, is_success, status)


if __name__ == "__main__":
    main()
