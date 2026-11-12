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
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv

from ..core.constants import (
    LOGIN_API_ROOT_DEFAULT,
    PROVIDER_NAME,
    GET_CURRENT_TASK_STATUS_SCRIPT_NAME,
)
from ..core.MicrosoftDefenderATPManager import (
    MicrosoftDefenderATPManager,
    MicrosoftDefenderATPError,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_CURRENT_TASK_STATUS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    login_api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Login API Root",
        default_value=LOGIN_API_ROOT_DEFAULT,
        is_mandatory=True,
    )

    api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Api Root",
        input_type=str,
        is_mandatory=True,
    )

    client_id = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Client ID",
        input_type=str,
        is_mandatory=True,
    )

    client_secret = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Client Secret",
        input_type=str,
        is_mandatory=True,
    )

    tenant_id = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Azure Active Directory ID",
        input_type=str,
        is_mandatory=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        default_value=False,
    )

    task_ids = extract_action_param(
        siemplify, param_name="Task IDs", input_type=str, is_mandatory=True
    )

    task_ids = MicrosoftDefenderATPManager.convert_comma_separated_to_list(task_ids)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:

        microsoft_defender_atp = MicrosoftDefenderATPManager(
            client_id=client_id,
            client_secret=client_secret,
            tenant_id=tenant_id,
            resource=api_root,
            login_api_root=login_api_root,
            verify_ssl=verify_ssl,
        )

        tasks = []
        succeeded_tasks = []
        failed_tasks = []
        output_messages = []

        for task_id in task_ids:
            try:
                task = microsoft_defender_atp.get_machine_task_status(id=task_id)
                tasks.append(task)
                msg = f"Status {task.status} of task with ID {task.id} was successfully obtained"
                output_messages.append(msg)
                siemplify.LOGGER.info(msg)
                succeeded_tasks.append(task.id)
            except MicrosoftDefenderATPError as e:
                failed_tasks.append(task_id)
                siemplify.LOGGER.error(e)
                siemplify.LOGGER.exception(e)

        if succeeded_tasks:
            output_messages.append(
                f"{len(succeeded_tasks)} task's statuses were obtained"
            )

        if failed_tasks:
            output_messages.append(
                f"{len(failed_tasks)} task's were statuses were failed to obtain"
            )
            output_messages.append(
                f"Failed to get tasks statuses with ID: {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(failed_tasks)}"
            )
            result = "false"
        else:
            result = "true"

        if tasks:
            siemplify.result.add_result_json([task.to_json() for task in tasks])

            siemplify.result.add_data_table(
                title="Current Task Status:",
                data_table=construct_csv([task.to_table() for task in tasks]),
            )

        output_message = "\n".join(output_messages)
        status = EXECUTION_STATE_COMPLETED

    except MicrosoftDefenderATPError as e:
        output_message = f"Action didn't completed due to error: {e}"
        result = "false"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
