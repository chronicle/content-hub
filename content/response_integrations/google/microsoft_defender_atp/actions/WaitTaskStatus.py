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
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)

from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv

from ..core.constants import (
    LOGIN_API_ROOT_DEFAULT,
    PROVIDER_NAME,
    WAIT_TASK_STATUS_SCRIPT_NAME,
)
from ..core.MicrosoftDefenderATPManager import (
    MicrosoftDefenderATPManager,
    MicrosoftDefenderATPError,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = WAIT_TASK_STATUS_SCRIPT_NAME
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

        succeeded_tasks = []
        pending_tasks = []

        for task_id in task_ids:
            task = microsoft_defender_atp.get_machine_task_status(id=task_id)

            if task.is_succeeded:
                succeeded_tasks.append(task)
            elif task.is_pending or task.is_in_progress:
                pending_tasks.append(task)
            else:
                output_message = (
                    f"Task with ID {task.id} finished with status {task.status}"
                )
                result = "false"
                status = EXECUTION_STATE_COMPLETED

                if succeeded_tasks:
                    siemplify.result.add_result_json(
                        [task.to_json() for task in succeeded_tasks]
                    )

                    siemplify.result.add_data_table(
                        title="Current Task Status:",
                        data_table=construct_csv(
                            [task.to_table() for task in succeeded_tasks]
                        ),
                    )

                siemplify.end(output_message, result, status)

        if not pending_tasks:
            output_message = f'{len(succeeded_tasks) if len(succeeded_tasks) else "No"} Tasks were awaited'
            result = "true"
            status = EXECUTION_STATE_COMPLETED
            siemplify.LOGGER.info(output_message)

            if succeeded_tasks:
                siemplify.result.add_result_json(
                    [task.to_json() for task in succeeded_tasks]
                )

                siemplify.result.add_data_table(
                    title="Current Task Status:",
                    data_table=construct_csv(
                        [task.to_table() for task in succeeded_tasks]
                    ),
                )
        else:
            output_message = f"{len(pending_tasks)} tasks should be awaited"
            result = "false"
            status = EXECUTION_STATE_INPROGRESS

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
