from __future__ import annotations
import base64
import os

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import InsightSeverity, InsightType
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_configuration_param, extract_action_param

from ..core.constants import (
    DOWNLOAD_REPORT_PREVIEW_ACTION,
    INTEGRATION_NAME,
    JPG_FORMAT,
    JPG_FILE_NAME,
    PNG_FORMAT,
    PNG_FILE_NAME,
)
from ..core.CofenseTriageExceptions import RecordNotFoundException
from ..core.CofenseTriageManager import CofenseTriageManager
from ..core.UtilsManager import save_image_attachment


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DOWNLOAD_REPORT_PREVIEW_ACTION
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        print_value=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
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

    report_id = extract_action_param(
        siemplify,
        param_name="Report ID",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )
    download_folder = extract_action_param(
        siemplify,
        param_name="Download Folder",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )
    image_format = extract_action_param(
        siemplify,
        param_name="Image Format",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )
    overwrite = extract_action_param(
        siemplify,
        param_name="Overwrite",
        is_mandatory=False,
        default_value=False,
        print_value=True,
        input_type=bool,
    )
    create_insight = extract_action_param(
        siemplify,
        param_name="Create Insight",
        is_mandatory=False,
        default_value=False,
        print_value=True,
        input_type=bool,
    )

    output_message = ""
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    json_results = {}
    file_name = ""
    if not download_folder.endswith("/"):
        download_folder = f"{download_folder}{'/'}"

    if image_format == JPG_FORMAT:
        file_name = JPG_FILE_NAME.format(report_id)

    if image_format == PNG_FORMAT:
        file_name = PNG_FILE_NAME.format(report_id)

    absolute_file_path = f"{download_folder}{file_name}"

    if not overwrite:
        if os.path.exists(absolute_file_path):
            status = EXECUTION_STATE_FAILED
            result_value = False
            output_message += (f'Error executing action '
                               f'{DOWNLOAD_REPORT_PREVIEW_ACTION}. Reason: '
                               f'File with that file path already exists. '
                               f'Please remove it or set "Overwrite" to true')
            siemplify.LOGGER.error(output_message)
            siemplify.LOGGER.info("----------------- Main - Finished -----------------")
            siemplify.LOGGER.info(
                f"\n  status: {status}\n  "
                f"result_value: {result_value}\n  "
                f"output_message: {output_message}"
            )
            siemplify.end(output_message, result_value, status)

    try:
        cofensetriage_manager = CofenseTriageManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
        )

        email_report = cofensetriage_manager.download_report_preview(
            report_id=report_id, image_format=image_format
        )
        absolute_file_path = save_image_attachment(
            path=download_folder, name=file_name, content=email_report.raw
        )

        json_results = {"absolute_file_path": absolute_file_path}

        with open(absolute_file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())

        if create_insight:
            siemplify.create_case_insight(
                triggered_by=INTEGRATION_NAME,
                title=f"Report {report_id}. Preview",
                content=f'<img src="data:image/jpeg;base64,'
                        f'{encoded_string.decode("utf-8")}">',
                entity_identifier="",
                severity=InsightSeverity.INFO,
                insight_type=InsightType.General,
            )

        output_message += (f"Successfully downloaded preview related to the "
                           f"report with ID {report_id} in {INTEGRATION_NAME}")
        siemplify.result.add_result_json(json_results)

    except RecordNotFoundException as e:
        output_message += (f"Action wasn't able to download a preview related to "
                           f"the report with ID {report_id} in "
                           f"{DOWNLOAD_REPORT_PREVIEW_ACTION}. Reason:\n {e}")
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False

    except Exception as e:
        output_message += (
            f"Error executing action {DOWNLOAD_REPORT_PREVIEW_ACTION}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  "
        f"result_value: {result_value}\n  "
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
