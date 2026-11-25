from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from ..core.PortnoxManager import PortnoxManager, PortnoxAuthError

INTEGRATION_NAME = "PortnoxCloud"
SCRIPT_NAME = "Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "{0} - {1}".format(INTEGRATION_NAME, SCRIPT_NAME)
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    api_root = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name="API Root",
        default_value="https://clear.portnox.com:8081/CloudPortalBackEnd/")
    api_token = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name="API Token", is_mandatory=False)
    username = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name="Username", is_mandatory=False)
    password = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name="Password", is_mandatory=False)
    verify_ssl = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name="Verify SSL",
        input_type=bool, default_value=True)

    try:
        manager = PortnoxManager(
            api_root=api_root, api_token=api_token, username=username,
            password=password, verify_ssl=verify_ssl, logger=siemplify.LOGGER)
        manager.test_connectivity()
        status = EXECUTION_STATE_COMPLETED
        result_value = True
        output_message = "Successfully connected to the Portnox Cloud server at {0}".format(api_root)

    except PortnoxAuthError as error:
        siemplify.LOGGER.error(str(error))
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = "Authentication to Portnox Cloud failed. {0}".format(error)

    except Exception as error:
        siemplify.LOGGER.error("Ping failed: {0}".format(error))
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = "Failed to connect to the Portnox Cloud server. Error: {0}".format(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
