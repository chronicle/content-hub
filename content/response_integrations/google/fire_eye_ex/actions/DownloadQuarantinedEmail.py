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

# coding=utf-8
from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.FireEyeEXManager import (
    FireEyeEXManager,
    FireEyeEXUnsuccessfulOperationError,
    FireEyeEXDownloadFileError,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param
import base64
from urllib.parse import urljoin

INTEGRATION_NAME = "FireEyeEX"
SCRIPT_NAME = "Download Quarantined Email"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        input_type=str,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        input_type=str,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        input_type=str,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    queue_id = extract_action_param(
        siemplify,
        param_name="Queue ID",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )
    download_path = extract_action_param(
        siemplify,
        param_name="Download Path",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = "true"

    try:
        ex_manager = FireEyeEXManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )
        email_content = ex_manager.download_quarantined_email(queue_id)

        try:
            siemplify.result.add_attachment(
                f"Quarantined_email_{queue_id}.eml",
                f"Quarantined_email_{queue_id}.eml",
                base64.b64encode(email_content.content.encode("utf-8")),
            )
            output_message = f"Successfully downloaded FireEye EX quarantined email with queue id {queue_id}!"

            absolute_path = urljoin(download_path, f"Quarantined_email_{queue_id}.eml")

            if ex_manager.save_artifacts_to_file(email_content, absolute_path):
                siemplify.result.add_result_json({"file_path": absolute_path})
                output_message = f"Successfully downloaded FireEye EX quarantined email with queue id {queue_id}!"
            else:
                output_message = f"Action wasn’t able to download FireEye EX alert quarantined email with queue id {queue_id}. Reason: File with that path already exists."
                result_value = "false"

        except FireEyeEXDownloadFileError as e:
            siemplify.LOGGER.error(
                f"Unable to attach downloaded artifacts. Reason: {e}"
            )
            output_message = f"Unable to attach downloaded artifacts. Reason: {e}"
            result_value = "false"

        except EnvironmentError:
            # File size is too big
            siemplify.LOGGER.error(
                "Unable to attach quarantined email. Reason: email is too large in size."
            )
            output_message = "Unable to attach quarantined email. Reason: email is too large in size."
            result_value = "false"

        ex_manager.logout()

    except FireEyeEXUnsuccessfulOperationError as e:
        siemplify.LOGGER.error(f"Email with queue id {queue_id} was not downloaded.")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Email with queue id {queue_id} was not downloaded. Reason: {e}"
        )
        result_value = "false"

    except Exception as e:
        siemplify.LOGGER.error(
            f'Error executing action "Download Quarantined Email". Reason: {e}'
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = (
            f'Error executing action "Download Quarantined Email". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
