from __future__ import annotations
from ..core.FireEyeCMConstants import (
    PROVIDER_NAME,
    EX_APPLIANCE_TYPE,
    EX_APPLIANCE_NAME,
    DELETE_QUARANTINED_EMAIL_SCRIPT_NAME,
)
from ..core.FireEyeCMExceptions import (
    FireEyeCMUnsuccessfulOperationError,
    FireEyeCMSensorApplianceNotFound,
)
from ..core.FireEyeCMManager import FireEyeCMManager
from TIPCommon import extract_configuration_param, extract_action_param

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DELETE_QUARANTINED_EMAIL_SCRIPT_NAME

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
    queue_id = extract_action_param(
        siemplify, param_name="Queue ID", is_mandatory=True, print_value=True
    )
    sensor_name = extract_action_param(
        siemplify,
        param_name="Sensor Name",
        is_mandatory=False,
        default_value=None,
        print_value=True,
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

        if not sensor_name:  # Auto-discover suitable appliance in FireEye CM
            siemplify.LOGGER.info(
                f"Searching for suitable {EX_APPLIANCE_NAME} appliance in {PROVIDER_NAME}"
            )
            sensor_names = manager.get_sensor_names(product=EX_APPLIANCE_TYPE)
            siemplify.LOGGER.info(
                f"Found {len(sensor_names)} suitable appliances in {PROVIDER_NAME}."
            )

            if not sensor_names:  # No suitable appliances were found in FireEye CM
                raise FireEyeCMSensorApplianceNotFound(
                    f'Sensor for {EX_APPLIANCE_NAME} appliance was not found. Please provide it manually in the "Sensor Name" parameter.'
                )

            siemplify.LOGGER.info(
                f'Taking first matching appliance with sensor name "{sensor_names[0]}" out of all available appliances: '
                f"{', '.join(sensor_names)} in {PROVIDER_NAME}"
            )
            sensor_name = sensor_names[0]
        else:
            siemplify.LOGGER.info(
                f'Checking if user provided sensor name "{sensor_name}" exists in {PROVIDER_NAME}'
            )

            if sensor_name not in manager.get_sensor_names(product=EX_APPLIANCE_TYPE):
                raise FireEyeCMSensorApplianceNotFound(
                    f"Sensor with name {sensor_name} was not found. Please check the spelling."
                )

            siemplify.LOGGER.info(
                f"Successfully verified sensor name {sensor_name} existence in {PROVIDER_NAME}"
            )

        siemplify.LOGGER.info(f"Deleting quarantined email with queue id {queue_id}")
        manager.delete_quarantined_email(sensor_name=sensor_name, queue_id=queue_id)

        result_value = True
        output_message = f"Successfully deleted {PROVIDER_NAME} quarantined email with queue id {queue_id}!"

    except FireEyeCMSensorApplianceNotFound as error:
        output_message = (
            f'Error executing action "Delete Quarantined Email". Reason: {error}'
        )
        siemplify.LOGGER.error(error)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED

    except FireEyeCMUnsuccessfulOperationError as error:
        output_message = (
            f'Email with queue id "{queue_id}" was not deleted. Reason: {error}'
        )
        siemplify.LOGGER.error(error)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED

    except Exception as error:
        output_message = (
            f'Error executing action "Delete Quarantined Email". Reason: {error}'
        )
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
