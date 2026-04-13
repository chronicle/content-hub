# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from ..core.UrlScanManager import UrlScanManager
from ..core.constants import (
    INTEGRATION_NAME,
    GET_SCAN_FULL_DETAILS_SCRIPT_NAME,
    WEB_REPORT_LINK_TITLE,
    DOM_TREE_LINK_TITLE,
    ATTACHMENT_TITLE,
    ATTACHMENT_FILE_NAME,
)
from ..core.UtilsManager import get_screenshot_content_base64


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_SCAN_FULL_DETAILS_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    # INIT INTEGRATION CONFIGURATIONS:
    api_key = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Key"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    scan_ids_string = extract_action_param(
        siemplify,
        param_name="Scan ID",
        print_value=True,
        default_value=False,
        is_mandatory=True,
    )
    scan_ids = [scan_id.strip() for scan_id in scan_ids_string.split(",") if scan_id.strip()]
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    scan_result = []
    failed_ids = []
    output_message = ""

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = UrlScanManager(
            api_key=api_key, verify_ssl=verify_ssl, force_check_connectivity=True
        )

        for scan_id in scan_ids:
            try:
                scan_result.append(manager.get_scan_report_by_id(scan_id))
            except Exception as err:
                failed_ids.append(scan_id)
                siemplify.LOGGER.error(
                    f"Action wasn’t able to fetch results for the following scan: {scan_id}"
                )
                siemplify.LOGGER.exception(err)

        for index in range(len(scan_result)):
            details = scan_result[index]
            siemplify.result.add_link(
                WEB_REPORT_LINK_TITLE.format(INTEGRATION_NAME, details.uuid),
                details.report_url,
            )
            siemplify.result.add_link(
                DOM_TREE_LINK_TITLE.format(INTEGRATION_NAME, details.uuid),
                details.dom_url,
            )
            try:
                screenshot_content = manager.get_screenshot_content(url=details.screenshot_url)
                base64_screenshot = get_screenshot_content_base64(screenshot_content)
                siemplify.result.add_attachment(
                    title=ATTACHMENT_TITLE.format(index + 1),
                    filename=ATTACHMENT_FILE_NAME.format(details.uuid),
                    file_contents=base64_screenshot.decode(),
                )
            except Exception as e:
                siemplify.LOGGER.error(e)
                siemplify.LOGGER.exception(e)

        if scan_result:
            output_message += f"Successfully fetched results for the following scans: {', '.join([details.uuid for details in scan_result])}\n"
            siemplify.result.add_result_json([result.to_json() for result in scan_result])

        if failed_ids:
            output_message += f"Action wasn’t able to fetch results for the following scans: {', '.join([failed_id for failed_id in failed_ids])}"

        if not scan_result:
            result_value = False
            output_message = f"Action wasn’t able to fetch results. The provided scan ids are not available using {INTEGRATION_NAME}"

    except Exception as e:
        output_message = (
            f"Error executing action '{GET_SCAN_FULL_DETAILS_SCRIPT_NAME}'. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
