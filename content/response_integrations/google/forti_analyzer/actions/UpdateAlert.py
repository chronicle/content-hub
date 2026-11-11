from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from forti_analyzer.core.FortiAnalyzerManager import FortiAnalyzerManager
from forti_analyzer.core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    UPDATE_ALERT_SCRIPT_NAME,
    ACKNOWLEDGEMENT_MAPPING,
    SELECT_ONE,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_ALERT_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
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

    # action parameters
    alert_id = extract_action_param(
        siemplify, param_name="Alert ID", is_mandatory=True, print_value=True
    )
    acknowledge_status = extract_action_param(
        siemplify, param_name="Acknowledge Status", print_value=True
    )
    mark_as_read = extract_action_param(
        siemplify, param_name="Mark As Read", input_type=bool, print_value=True
    )
    assign_to = extract_action_param(
        siemplify, param_name="Assign To", print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result = True
    output_message = ""
    manager = None

    try:
        if acknowledge_status == SELECT_ONE and not mark_as_read and not assign_to:
            raise Exception(
                'at least one of the "Acknowledge Status", "Mark As Read" '
                'or "Assign To" parameters should have a value.'
            )

        manager = FortiAnalyzerManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        alert = manager.find_alert(alert_id=alert_id)

        if not alert:
            raise Exception(
                f"alert with ID {alert_id} wasn't found in {INTEGRATION_DISPLAY_NAME}. Please check the spelling."
            )

        if acknowledge_status != SELECT_ONE:
            manager.acknowledge_alert(
                alert_id=alert_id,
                adom=alert.adom,
                username=username,
                acknowledge=ACKNOWLEDGEMENT_MAPPING.get(acknowledge_status),
            )

        if mark_as_read:
            manager.mark_as_read(alert_id=alert_id, adom=alert.adom)

        if assign_to:
            manager.assign_user(alert_id=alert_id, adom=alert.adom, username=assign_to)

        alert = manager.find_alert(alert_id=alert_id)
        siemplify.result.add_result_json(alert.to_json())
        output_message += f'Successfully updated alert with ID "{alert_id}" in {INTEGRATION_DISPLAY_NAME}'

    except Exception as e:
        result = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(
            f"General error performing action {UPDATE_ALERT_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        output_message = (
            f'Error executing action "{UPDATE_ALERT_SCRIPT_NAME}". Reason: {e}'
        )

    finally:
        try:
            if manager:
                manager.logout()
                siemplify.LOGGER.info(
                    f"Successfully logged out from {INTEGRATION_DISPLAY_NAME}"
                )
        except Exception as e:
            siemplify.LOGGER.error(f"Logging out failed. Error: {e}")
            siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
