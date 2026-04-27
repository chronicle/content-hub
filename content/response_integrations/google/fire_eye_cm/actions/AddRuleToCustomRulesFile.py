from __future__ import annotations
import os

from TIPCommon import extract_configuration_param, extract_action_param

from ..core.FireEyeCMConstants import (
    PROVIDER_NAME,
    NX_APPLIANCE_TYPE,
    NX_APPLIANCE_NAME,
    TEMP_CUSTOM_RULES_FILE_NAME,
    ADD_RULE_TO_CUSTOM_RULES_FILE_SCRIPT_NAME,
)
from ..core.FireEyeCMExceptions import (
    FireEyeCMSensorApplianceNotFound,
    FireEyeCMDownloadFileError,
    FireEyeCMUnsuccessfulOperationError,
)
from ..core.FireEyeCMManager import FireEyeCMManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyUtils import unix_now
from ..core.UtilsManager import create_custom_rules_file, append_artifacts_to_file


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_RULE_TO_CUSTOM_RULES_FILE_SCRIPT_NAME
    action_execution_time = unix_now()
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
    rule = extract_action_param(
        siemplify, param_name="Rule", is_mandatory=True, print_value=True
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

    # Create temp custom Snort rules file
    rules_file_path = os.path.join(
        siemplify.run_folder, TEMP_CUSTOM_RULES_FILE_NAME.format(action_execution_time)
    )

    try:
        manager = FireEyeCMManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        if not sensor_name:  # Auto-discover suitable appliance in FireEye NX
            siemplify.LOGGER.info(
                f"Searching for suitable {NX_APPLIANCE_NAME} appliance in {PROVIDER_NAME}"
            )
            sensor_names = manager.get_sensor_names(product=NX_APPLIANCE_TYPE)
            siemplify.LOGGER.info(
                f"Found {len(sensor_names)} suitable appliances in {PROVIDER_NAME}."
            )

            if not sensor_names:  # No suitable appliances were found in FireEye CM
                raise FireEyeCMSensorApplianceNotFound(
                    f'Sensor for {NX_APPLIANCE_NAME} appliance was not found. Please provide it manually in the "Sensor Name" parameter.'
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

            if sensor_name not in manager.get_sensor_names(product=NX_APPLIANCE_TYPE):
                raise FireEyeCMSensorApplianceNotFound(
                    f"Sensor with name {sensor_name} was not found. Please check the spelling."
                )

            siemplify.LOGGER.info(
                f"Successfully verified sensor name {sensor_name} existence in {PROVIDER_NAME}"
            )

        siemplify.LOGGER.info(f"Downloading custom Snort rules file")

        # Create custom snort rules file and append the rule
        create_custom_rules_file(
            siemplify=siemplify, file_path=rules_file_path, rule=f"{rule}\n"
        )

        # Append existing rules to the rules file
        rules_content = manager.download_custom_snort_rules_file(
            sensor_name=sensor_name
        )
        if not append_artifacts_to_file(
            response=rules_content, download_path=rules_file_path
        ):
            raise FireEyeCMDownloadFileError(
                "Failed to download and save snort rules file"
            )

        siemplify.LOGGER.info(
            f"Successfully downloaded custom snort rules file to path {rules_file_path}"
        )
        siemplify.LOGGER.info(f"Uploading custom rules file {rules_file_path}")
        manager.upload_custom_snort_rules_file(rules_file_path=rules_file_path)
        result_value = True
        output_message = f"Successfully added rule to custom rules file in {sensor_name} in {PROVIDER_NAME}!"

    except (FireEyeCMUnsuccessfulOperationError, FireEyeCMDownloadFileError) as error:
        output_message = f"Action wasn't able to add rule to the custom rules file in {PROVIDER_NAME}. Reason: {error}"
        siemplify.LOGGER.error(error)
        siemplify.LOGGER.exception(error)

    except FireEyeCMSensorApplianceNotFound as error:
        output_message = (
            f'Error executing action "Add Rule To Custom Rules File". Reason: {error}'
        )
        siemplify.LOGGER.error(error)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED

    except Exception as error:
        output_message = (
            f'Error executing action "Add Rule To Custom Rules File". Reason: {error}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED

    finally:
        try:
            try:
                siemplify.LOGGER.info("Cleaning created temp files..")
                # Clean temp custom rules file
                os.remove(rules_file_path)
                siemplify.LOGGER.info("Successfully cleaned temp files")
            except Exception as error:
                siemplify.LOGGER.error(error)
                siemplify.LOGGER.exception(error)

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
