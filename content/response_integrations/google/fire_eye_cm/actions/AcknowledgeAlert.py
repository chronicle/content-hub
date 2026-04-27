from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param

from ..core.FireEyeCMConstants import PROVIDER_NAME, ACKNOWLEDGE_ALERT_SCRIPT_NAME
from ..core.FireEyeCMExceptions import FireEyeCMNotFoundException, FireEyeCMValidationException
from ..core.FireEyeCMManager import FireEyeCMManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACKNOWLEDGE_ALERT_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Init Integration Configurations
    api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=False,
    )

    password = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Password",
        is_mandatory=True,
        print_value=False,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    # Init Action Parameters
    alert_uuid = extract_action_param(
        siemplify, param_name="Alert UUID", is_mandatory=True, print_value=True
    )
    annotation = extract_action_param(
        siemplify, param_name="Annotation", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_COMPLETED
    manager = None
    output_message = ""

    try:
        manager = FireEyeCMManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        try:
            siemplify.LOGGER.info(
                f"Trying to acknowledge alert {alert_uuid} in FireEye CM"
            )
            manager.acknowledge_alert(alert_uuid=alert_uuid, annotation=annotation)
            result_value = True
            output_message = (
                f"Successfully acknowledged {PROVIDER_NAME} alert with ID {alert_uuid}!"
            )
        except FireEyeCMValidationException as error:
            output_message = f"Action wasn't able to acknowledge {PROVIDER_NAME} alert with ID {alert_uuid}. Reason: {error}"
            siemplify.LOGGER.error(output_message)
            siemplify.LOGGER.exception(error)
        except FireEyeCMNotFoundException as error:
            output_message = (
                f"Action wasn't able to acknowledge {PROVIDER_NAME} alert with ID {alert_uuid}. Reason: Alert with ID "
                f"{alert_uuid} wasn't found."
            )
            siemplify.LOGGER.error(output_message)
            siemplify.LOGGER.exception(error)

    except Exception as error:
        output_message = f'Error executing action "Acknowledge Alert". Reason: {error}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED

    finally:
        try:
            if manager:
                siemplify.LOGGER.info(f"Logging out from {PROVIDER_NAME}..")
                manager.logout()
                siemplify.LOGGER.info(f"Successfully logged out from {PROVIDER_NAME}")
        except Exception as error:
            siemplify.LOGGER.error(f"Logging out failed. Error: {error}")
            siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
