from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.consts import INTEGRATION_NAME, DOWNLOAD_ALERT_CSV_ACTION
from ..core.IntsightsManager import IntsightsManager
from ..core.exceptions import AlertNotFoundError, IntsightsAlreadyExistsError, NotFoundError
from ..core.utils import save_file
import os


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DOWNLOAD_ALERT_CSV_ACTION
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )
    account_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Account ID",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Key",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    alert_id = extract_action_param(
        siemplify, param_name="Alert ID", is_mandatory=True, print_value=True
    )
    download_folder_path = extract_action_param(
        siemplify,
        param_name="Download Folder Path",
        is_mandatory=True,
        print_value=True,
    )
    overwrite = extract_action_param(
        siemplify, param_name="Overwrite", input_type=bool, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_FAILED

    try:
        # Raise an error if path does not exist
        if not os.path.exists(download_folder_path):
            raise Exception("Specified path doesn't exist.")

        intsight_manager = IntsightsManager(
            server_address=api_root,
            account_id=account_id,
            api_key=api_key,
            api_login=False,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )

        response = intsight_manager.download_alert_csv(alert_id=alert_id)
        absolute_file_path = save_file(
            path=download_folder_path,
            name=alert_id,
            content=response,
            overwrite=overwrite,
        )
        siemplify.result.add_result_json({"absolute_path": absolute_file_path})
        output_message = f"Successfully downloaded CSV for the alert with ID {alert_id} in {INTEGRATION_NAME}"
        result_value = True
        status = EXECUTION_STATE_COMPLETED

    except AlertNotFoundError as e:
        siemplify.LOGGER.exception(e)
        output_message = f"No CSV information was found for the alert with ID {alert_id} in {INTEGRATION_NAME}"
        result_value = True
        status = EXECUTION_STATE_COMPLETED
        siemplify.result.add_result_json({"absolute_path": ""})

    except IntsightsAlreadyExistsError as e:
        output_message = (
            f'Error executing action "{DOWNLOAD_ALERT_CSV_ACTION}". Reason: file with path {e} '
            f'already exists. Please delete the file or set "Overwrite" to true.'
        )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {DOWNLOAD_ALERT_CSV_ACTION}"
        )
        siemplify.LOGGER.exception(e)
        output_message = (
            f'Error executing action "{DOWNLOAD_ALERT_CSV_ACTION}". Reason: {e}'
        )
        if isinstance(e, NotFoundError):
            output_message = (
                f'Error executing action "{DOWNLOAD_ALERT_CSV_ACTION}". Reason: Unable '
                f"to find alert with ID {alert_id}."
            )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
