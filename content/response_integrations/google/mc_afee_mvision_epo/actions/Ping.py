from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.McAfeeMvisionEPOManager import McAfeeMvisionEPOManager
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param
from ..core.constants import PING_SCRIPT_NAME, INTEGRATION_NAME
from ..core.exceptions import GroupNotFoundException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
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
        default_value=True,
        input_type=bool,
    )

    scopes = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Scopes",
        is_mandatory=True,
    )

    group_name = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Group Name"
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_FAILED
    connectivity_result = False
    try:
        manager = McAfeeMvisionEPOManager(
            api_root,
            client_id,
            client_secret,
            scopes,
            group_name,
            verify_ssl,
            siemplify.LOGGER,
        )
        output_message = "Successfully connected to the McAfee Mvision ePO server with the provided connection parameters!"
        siemplify.LOGGER.info(output_message)
        connectivity_result = True
        status = EXECUTION_STATE_COMPLETED
    except GroupNotFoundException as e:
        output_message = f"Group {group_name} was not found in McAfee Mvision ePO. Please check for any spelling mistakes."
        siemplify.LOGGER.error(output_message)
    except Exception as e:
        output_message = (
            f"Failed to connect to the McAfee Mvision ePO server! Error is {e}"
        )
        siemplify.LOGGER.error(
            f"Connection to API failed, performing action {PING_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)

    siemplify.end(output_message, connectivity_result, status)


if __name__ == "__main__":
    main()
