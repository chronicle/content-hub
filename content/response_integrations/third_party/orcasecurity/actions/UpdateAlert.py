from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.OrcaSecurityManager import OrcaSecurityManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    UPDATE_ALERT_SCRIPT_NAME,
    SNOOZE_STATE_MAPPING,
    STATUS_MAPPING,
    DEFAULT_SNOOZE_DAYS,
)
from ..core.OrcaSecurityExceptions import OrcaSecurityDuplicatedDataException


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
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=False,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    # action parameters
    alert_id = extract_action_param(
        siemplify, param_name="Alert ID", is_mandatory=True, print_value=True
    )
    verify_alert = extract_action_param(
        siemplify, param_name="Verify Alert", input_type=bool, print_value=True
    )
    snooze_state = extract_action_param(siemplify, param_name="Snooze State", print_value=True)
    snooze_days = extract_action_param(
        siemplify,
        param_name="Snooze Days",
        input_type=int,
        default_value=DEFAULT_SNOOZE_DAYS,
        print_value=True,
    )
    alert_status = extract_action_param(siemplify, param_name="Status", print_value=True)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result = True
    output_message = ""
    already_updated_status = False

    try:
        if (
            not SNOOZE_STATE_MAPPING.get(snooze_state)
            and not STATUS_MAPPING.get(alert_status)
            and not verify_alert
        ):
            raise Exception(
                'at least one of the following parameters needs to be provided: "Status", "Verify '
                'Alert", "Snooze State"'
            )

        if snooze_state == SNOOZE_STATE_MAPPING.get("Snooze") and not snooze_days:
            raise Exception('"Snooze Day" needs to be provided.')

        manager = OrcaSecurityManager(
            api_root=api_root,
            api_key=api_key,
            api_token=api_token,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        if verify_alert:
            manager.verify_alert(alert_id)

        if snooze_state == SNOOZE_STATE_MAPPING.get("Snooze"):
            manager.snooze_alert(alert_id, snooze_days)

        try:
            if snooze_state == SNOOZE_STATE_MAPPING.get("Unsnooze") and not STATUS_MAPPING.get(
                alert_status
            ):
                manager.update_alert_status(alert_id, STATUS_MAPPING.get("Open"))

            if STATUS_MAPPING.get(alert_status):
                manager.update_alert_status(alert_id, STATUS_MAPPING.get(alert_status))
        except OrcaSecurityDuplicatedDataException:
            already_updated_status = True
            output_message += (
                f'Alert with ID "{alert_id}" already has status '
                f'"{alert_status if STATUS_MAPPING.get(alert_status) else "Open"}" '
                f"in {INTEGRATION_DISPLAY_NAME}.\n"
            )

        alert = manager.get_alert_data(alert_id)
        siemplify.result.add_result_json(alert.to_json())

        if not already_updated_status or (
            verify_alert or snooze_state == SNOOZE_STATE_MAPPING.get("Snooze")
        ):
            output_message += (
                f'Successfully updated alert with ID "{alert_id}" in {INTEGRATION_DISPLAY_NAME}'
            )

    except Exception as e:
        result = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(f"General error performing action {UPDATE_ALERT_SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        output_message = f'Error executing action "{UPDATE_ALERT_SCRIPT_NAME}". Reason: {e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
