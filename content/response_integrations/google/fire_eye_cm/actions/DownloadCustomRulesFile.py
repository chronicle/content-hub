from __future__ import annotations
import os

from ..core.FireEyeCMConstants import (
    PROVIDER_NAME,
    NX_APPLIANCE_TYPE,
    NX_APPLIANCE_NAME,
    DOWNLOADED_CUSTOM_RULES_FILE_NAME,
    DOWNLOAD_CUSTOM_RULES_FILE_SCRIPT_NAME,
)
from ..core.FireEyeCMExceptions import (
    FireEyeCMUnsuccessfulOperationError,
    FireEyeCMSensorApplianceNotFound,
    FireEyeCMDownloadFileError,
)
from ..core.FireEyeCMManager import FireEyeCMManager
from TIPCommon import extract_configuration_param, extract_action_param

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.UtilsManager import save_artifacts_to_file


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DOWNLOAD_CUSTOM_RULES_FILE_SCRIPT_NAME

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
    sensor_name = extract_action_param(
        siemplify,
        param_name="Sensor Name",
        is_mandatory=False,
        default_value=None,
        print_value=True,
    )
    download_folder_path = extract_action_param(
        siemplify,
        param_name="Download Folder Path",
        is_mandatory=True,
        print_value=True,
    )
    download_file_path = download_folder_path
    overwrite = extract_action_param(
        siemplify,
        param_name="Overwrite",
        default_value=True,
        is_mandatory=True,
        input_type=bool,
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

        # If download path was provided as folder, action uses pre-defined filename
        if os.path.exists(download_folder_path) and os.path.isdir(download_folder_path):
            download_file_path = os.path.join(
                download_folder_path, DOWNLOADED_CUSTOM_RULES_FILE_NAME
            )
            siemplify.LOGGER.info(
                f"Provided with download folder path {download_folder_path}. Created download file path {download_file_path}"
            )

        # Download path folders should exist
        elif not os.path.exists(os.path.dirname(download_folder_path)):
            raise FireEyeCMDownloadFileError(
                f"Download folder path {download_folder_path} was not found."
            )

        # Check if file exists and overwrite is forbidden
        if os.path.exists(download_file_path) and not overwrite:
            raise FireEyeCMDownloadFileError(
                f"Download folder path {download_file_path} already exists."
            )

        siemplify.LOGGER.info(f"Absolute download file path: {download_file_path}")

        if not sensor_name:  # Auto-discover suitable appliance in FireEye CM
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

        siemplify.LOGGER.info(f"Downloading custom rules file")

        rules_content = manager.download_custom_snort_rules_file(
            sensor_name=sensor_name
        )

        if not save_artifacts_to_file(
            response=rules_content,
            download_path=download_file_path,
            overwrite=overwrite,
        ):
            raise FireEyeCMDownloadFileError(
                "Failed to download and save custom snort rules file"
            )

        result_value = True
        output_message = f"Successfully downloaded custom rules file from appliance {sensor_name} in {PROVIDER_NAME}!"
        siemplify.result.add_result_json({"file_path": download_file_path})

    except FireEyeCMSensorApplianceNotFound as error:
        output_message = (
            f'Error executing action "Download Custom Rules File". Reason: {error}'
        )
        siemplify.LOGGER.error(error)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED

    except (FireEyeCMUnsuccessfulOperationError, FireEyeCMDownloadFileError) as error:
        output_message = f"Action wasn't able to download custom rules file from appliance {sensor_name} in {PROVIDER_NAME}. Reason: {error}"
        siemplify.LOGGER.error(error)
        siemplify.LOGGER.exception(error)

    except Exception as error:
        output_message = (
            f'Error executing action "Download Custom Rules File". Reason: {error}'
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
