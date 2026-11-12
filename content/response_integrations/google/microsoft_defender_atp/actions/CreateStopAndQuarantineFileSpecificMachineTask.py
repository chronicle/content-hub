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
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv

from ..core.constants import (
    LOGIN_API_ROOT_DEFAULT,
    PROVIDER_NAME,
    CREATE_STOP_AND_QUARANTINE_FILE_SPECIFIC_MACHINE_TASK_SCRIPT_NAME,
)
from ..core.MicrosoftDefenderATPManager import (
    MicrosoftDefenderATPManager,
    MicrosoftDefenderATPError,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = (
        CREATE_STOP_AND_QUARANTINE_FILE_SPECIFIC_MACHINE_TASK_SCRIPT_NAME
    )
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

    file_hash = extract_action_param(
        siemplify,
        param_name="SHA1 File Hash to Quarantine",
        input_type=str,
        is_mandatory=True,
    )

    comment = extract_action_param(
        siemplify, param_name="Comment", input_type=str, is_mandatory=True
    )

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
        succeeded_entities = set()
        missing_entities = set()
        failed_entities = set()
        output_messages = []

        for entity in siemplify.target_entities:
            siemplify.LOGGER.info(f"Start processing entity {entity.identifier}")

            try:
                if entity.entity_type == EntityTypes.HOSTNAME:
                    machines = microsoft_defender_atp.get_machines_by_name(
                        starts_with_name=entity.identifier
                    )
                elif entity.entity_type == EntityTypes.ADDRESS:
                    machines = microsoft_defender_atp.get_machines(ip=entity.identifier)
                else:
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} is of unsupported type {entity.entity_type}, skipping..."
                    )
                    continue
            except MicrosoftDefenderATPError as e:
                siemplify.LOGGER.error(f"Error occurred: {e}")
                siemplify.LOGGER.exception(e)
                failed_entities.add(entity)
                continue

            if not machines:
                msg = f"Failed to find machine ATP by {entity.identifier} entity with type {entity.entity_type}"
                output_messages.append(msg)
                siemplify.LOGGER.warn(msg)
                missing_entities.add(entity)
                continue

            siemplify.LOGGER.info(
                f"Found {len(machines)} machines for entity {entity.identifier}"
            )

            found_machine = machines[-1]

            try:
                siemplify.LOGGER.info(
                    f"Initiating stop AV scan and quarantine file on machine {found_machine.id}"
                )
                task = microsoft_defender_atp.stop_and_quarantine_machine_file(
                    machine_id=found_machine.id, file_hash=file_hash, comment=comment
                )
                tasks.append(task)
                msg = f"Stop and quarantine file task {task.id} was created successfully on Defender ATP Server for {entity.identifier}"
                output_messages.append(msg)
                siemplify.LOGGER.info(msg)
                siemplify.LOGGER.info(
                    f"Processing {entity.identifier} entity succeeded"
                )
                succeeded_entities.add(entity)

            except MicrosoftDefenderATPError as e:
                output_messages.append(
                    f"Failed to process entity {entity.identifier}. {e}"
                )
                siemplify.LOGGER.error(e)
                siemplify.LOGGER.exception(e)
                siemplify.LOGGER.error(f"Processing {entity.identifier} entity failed")
                failed_entities.add(entity)

        # To remove all failed entities from succeeded entities
        succeeded_entities = succeeded_entities & failed_entities ^ succeeded_entities

        if succeeded_entities:
            output_messages.append(
                f"{len(succeeded_entities)} entities were successfully processed"
            )

        if missing_entities:
            output_messages.append(
                f"{len(missing_entities)} entities were not found in ATP"
            )

        if failed_entities:
            output_messages.append(f"{len(failed_entities)} entities failed")
            output_messages.append(
                f"Action failed to complete successfully on the following entities: {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string( [entity.identifier for entity in failed_entities] )}"
            )

            result = "false"
        else:
            output_messages.append("Action completed successfully")
            result = "true"

        if tasks:
            siemplify.result.add_result_json([task.to_json() for task in tasks])

            siemplify.result.add_data_table(
                title='Created Defender ATP "stop and quarantine a file" tasks:',
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
