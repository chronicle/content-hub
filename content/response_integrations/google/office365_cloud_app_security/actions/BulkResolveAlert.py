from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.Office365CloudAppSecurityManager import Office365CloudAppSecurityManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param

# =====================================
#             CONSTANTS               #
# =====================================
INTEGRATION_NAME = "Office365CloudAppSecurity"
SCRIPT_NAME = "Office365CloudAppSecurity - Bulk Resolve Alert"
ALERT_ID_SEPARATOR = ", "


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    result_value = "true"

    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="portal URL",
        input_type=str,
    )

    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API token",
        input_type=str,
    )

    # INIT ACTION PARAMETERS:
    alert_ids = extract_action_param(
        siemplify,
        param_name="Alert ID",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )
    comment = extract_action_param(
        siemplify, param_name="Comment", print_value=True, input_type=str
    )

    cloud_app_manager = Office365CloudAppSecurityManager(
        api_root=api_root, api_token=api_token
    )
    alert_id_list = alert_ids.split(ALERT_ID_SEPARATOR)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        status = EXECUTION_STATE_COMPLETED
        cloud_app_manager.bulk_resolve_alert(
            alert_id_list=alert_id_list,
            comment=comment,
        )
        output_message = f"The following alerts were resolved successfully:{alert_ids}"
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
