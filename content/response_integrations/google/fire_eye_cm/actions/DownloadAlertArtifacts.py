from __future__ import annotations
import os

from ..core.FireEyeCMConstants import (
    PROVIDER_NAME,
    DOWNLOADED_ALERT_ARTIFACTS,
    DOWNLOAD_ALERT_ARTIFACTS_SCRIPT_NAME,
)
from ..core.FireEyeCMExceptions import FireEyeCMDownloadFileError, FireEyeCMNotFoundException
from ..core.FireEyeCMManager import FireEyeCMManager
from TIPCommon import extract_configuration_param, extract_action_param

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.UtilsManager import save_artifacts_to_file


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DOWNLOAD_ALERT_ARTIFACTS_SCRIPT_NAME

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
    download_folder_path = extract_action_param(
        siemplify,
        param_name="Download Folder Path",
        is_mandatory=True,
        print_value=True,
    )
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

        # Absolute file path
        download_file_path = os.path.join(
            download_folder_path, DOWNLOADED_ALERT_ARTIFACTS.format(alert_uuid)
        )
        siemplify.LOGGER.info(f"Absolute file path: {download_file_path}")

        # Check if download file path already exists and overwriting is forbidden
        if os.path.exists(download_file_path) and not overwrite:
            raise FireEyeCMDownloadFileError(f"File with that path already exists.")

        # Check if download folder path exists
        if not os.path.exists(download_folder_path):
            raise FireEyeCMDownloadFileError(
                f"Download folder path {download_folder_path} was not found."
            )

        # Check if download folder path is a folder
        if not os.path.isdir(download_folder_path):
            raise FireEyeCMDownloadFileError(
                f"Download folder path {download_folder_path} must be a folder."
            )

        siemplify.LOGGER.info(
            f"Downloading alert artifacts for alert UUID {alert_uuid}"
        )

        zip_content = manager.download_alert_artifacts(alert_uuid=alert_uuid)

        if save_artifacts_to_file(
            response=zip_content, download_path=download_file_path, overwrite=overwrite
        ):
            siemplify.result.add_result_json({"file_path": download_file_path})
            output_message = f"Successfully downloaded {PROVIDER_NAME} alert artifacts with alert id {alert_uuid}!"
            result_value = True
        else:
            raise FireEyeCMDownloadFileError(
                f"Failed to save downloaded alert artifacts to local path {download_file_path}"
            )

    except FireEyeCMDownloadFileError as error:
        output_message = f"Action wasn't able to download {PROVIDER_NAME} alert artifacts with alert id {alert_uuid}. Reason: {error}"
        siemplify.LOGGER.error(error)
        siemplify.LOGGER.exception(error)

    except FireEyeCMNotFoundException as error:
        output_message = f"Artifacts for alert with uuid {alert_uuid} were not found."
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    except Exception as error:
        output_message = (
            f'Error executing action "Download Alert Artifacts". Reason: {error}'
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
