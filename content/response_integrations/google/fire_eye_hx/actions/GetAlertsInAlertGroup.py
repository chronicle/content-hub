from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.FireEyeHXManager import FireEyeHXManager
from soar_sdk.SiemplifyUtils import output_handler
from ..core.UtilsManager import convert_comma_separated_to_list

INTEGRATION_NAME = "FireEyeHX"
INTEGRATION_DISPLAY_NAME = "FireEye HX"
SCRIPT_NAME = "Get Alerts in Alert Group"
DEFAULT_LIMIT = 50


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        input_type=str,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        input_type=str,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        input_type=str,
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
        param_name="Limit",
        is_mandatory=False,
        input_type=int,
        print_value=True,
        default_value=DEFAULT_LIMIT,
    )

    alert_group_id = extract_action_param(
        siemplify,
        param_name="Alert Group ID",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )
    alert_group_ids = list(set(convert_comma_separated_to_list(alert_group_id)))

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    successful_groups = []
    failed_groups = []
    json_results = []

    if limit < 0:
        siemplify.LOGGER.info(
            f"Given value for Limit parameter is non-positive, will use default value of {DEFAULT_LIMIT}"
        )
        limit = DEFAULT_LIMIT

    try:
        hx_manager = FireEyeHXManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

        for group_id in alert_group_ids:
            try:
                alerts = hx_manager.get_alerts_by_alert_group_id(
                    alert_group_id=group_id, limit=limit
                )

                if alerts:
                    siemplify.LOGGER.info(
                        f"Found {len(alerts)} alerts for alert group ID {group_id}"
                    )
                    successful_groups.append(group_id)
                    siemplify.result.add_data_table(
                        f"FireEye HX Alert Group {group_id} Alerts",
                        construct_csv([alert.to_table() for alert in alerts]),
                    )
                    json_results.extend([alert.to_json(group_id) for alert in alerts])
                else:
                    failed_groups.append(group_id)

            except Exception as e:
                failed_groups.append(group_id)
                siemplify.LOGGER.error(
                    "Couldn't fetch details for the provided alert group ID {}. "
                    "Please check the provided ID and try again.".format(group_id)
                )
                siemplify.LOGGER.exception(e)

        if successful_groups:
            siemplify.result.add_result_json(json_results)
            output_message += "Successfully retrieved alerts related to the following Alert Groups in {}: \n{}".format(
                INTEGRATION_DISPLAY_NAME,
                "\n".join([group_id for group_id in successful_groups]),
            )

        if failed_groups:
            output_message += (
                "\nAction wasn't able to retrieve alerts related to the following Alert Groups in {}: "
                "\n{}".format(
                    INTEGRATION_DISPLAY_NAME,
                    "\n".join([group_id for group_id in failed_groups]),
                )
            )

        if not successful_groups:
            result_value = False
            output_message = f"None of the provided Alert Groups were found in {INTEGRATION_DISPLAY_NAME}"

    except Exception as e:
        siemplify.LOGGER.error(f"Failed to execute {SCRIPT_NAME} action, error is {e}.")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = f"Failed to execute {SCRIPT_NAME} action, error is {e}."

    finally:
        try:
            hx_manager.logout()
        except Exception as e:
            siemplify.LOGGER.error(f"Logging out failed. Error: {e}")
            siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
