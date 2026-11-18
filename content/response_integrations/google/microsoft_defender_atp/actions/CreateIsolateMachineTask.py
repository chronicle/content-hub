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
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import construct_csv

from ..core.constants import (
    CREATE_ISOLATE_MACHINE_TASK_SCRIPT_NAME,
    ISOLATE_ACTION_TYPE,
    LOGIN_API_ROOT_DEFAULT,
    MACHINE_ENTITY_TYPES,
    PROVIDER_NAME,
    ErrorType,
)
from ..core.exceptions import DefenderException
from ..core.MicrosoftDefenderATPManager import (
    MicrosoftDefenderATPError,
    MicrosoftDefenderATPManager,
    MicrosoftDefenderATPValidationError,
)
from ..core.UtilsManager import (
    ContainmentTaskSpec,
    ScopedSummaryLogger,
    classify_exception,
    create_containment_task_by_machine_id,
    start_or_reuse_containment_task,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_ISOLATE_MACHINE_TASK_SCRIPT_NAME
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

    isolation_type = extract_action_param(
        siemplify, param_name="Isolation Type", input_type=str, is_mandatory=True
    )

    comment = extract_action_param(
        siemplify, param_name="Comment", input_type=str, is_mandatory=True
    )
    machine_id: str | None = extract_action_param(siemplify, param_name="Machine ID", print_value=True)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    summary = ScopedSummaryLogger(siemplify, MACHINE_ENTITY_TYPES, machine_id)
    error: Exception | None = None

    # Validation block
    validation_errors = []

    try:
        MicrosoftDefenderATPManager.validate_isolation_type(isolation_type)
    except MicrosoftDefenderATPValidationError as e:
        validation_errors.append(e)

    if validation_errors:
        summary.log(EXECUTION_STATE_FAILED, validation_errors[0])
        siemplify.end(
            MicrosoftDefenderATPManager.join_validation_errors(validation_errors),
            "false",
            EXECUTION_STATE_FAILED,
        )

    try:
        microsoft_defender_atp = MicrosoftDefenderATPManager(
            client_id=client_id,
            client_secret=client_secret,
            tenant_id=tenant_id,
            resource=api_root,
            login_api_root=login_api_root,
            verify_ssl=verify_ssl,
        )
        containment_spec = ContainmentTaskSpec(
            action_type=ISOLATE_ACTION_TYPE,
            start_task=lambda target_id: microsoft_defender_atp.isolate_machine(
                machine_id=target_id,
                isolation_type=isolation_type,
                comment=comment,
            ),
            logger=siemplify.LOGGER,
        )

        tasks = []
        succeeded_entities = set()
        missing_entities = set()
        failed_entities = set()
        output_messages = []

        for entity in [] if machine_id else siemplify.target_entities:
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
                summary.target_results[entity.identifier] = classify_exception(e)[0]
                continue

            if not machines:
                msg = f"Failed to find machine ATP by {entity.identifier} entity with type {entity.entity_type}"
                output_messages.append(msg)
                siemplify.LOGGER.warn(msg)
                missing_entities.add(entity)
                summary.target_results[entity.identifier] = ErrorType.ENDPOINT_NOT_FOUND
                continue

            siemplify.LOGGER.info(
                f"Found {len(machines)} machines for entity {entity.identifier}"
            )
            found_machine = machines[-1]

            try:
                siemplify.LOGGER.info(
                    f"Initiating machine {found_machine.id} isolation"
                )
                task, outcome = start_or_reuse_containment_task(
                    microsoft_defender_atp,
                    found_machine.id,
                    containment_spec,
                )
                if task.id not in {existing.id for existing in tasks}:
                    tasks.append(task)
                msg = f"Isolate machine task {task.id} {outcome} on Defender ATP Server for {entity.identifier}"
                output_messages.append(msg)
                siemplify.LOGGER.info(msg)
                succeeded_entities.add(entity)
                summary.target_results[entity.identifier] = None

            except (MicrosoftDefenderATPError, DefenderException) as e:
                output_messages.append(
                    f"Failed to process entity {entity.identifier}. {e}"
                )
                siemplify.LOGGER.error(e)
                siemplify.LOGGER.exception(e)
                failed_entities.add(entity)
                summary.target_results[entity.identifier] = classify_exception(e)[0]

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
        elif tasks:
            output_messages.append("Action completed successfully")
            result = "true"
        else:
            result = "false"

        if machine_id:
            containment_result = create_containment_task_by_machine_id(
                microsoft_defender_atp,
                machine_id,
                containment_spec,
            )
            tasks = containment_result.tasks
            output_messages = containment_result.output_messages
            result = containment_result.result_value
            summary.target_results = {machine_id: containment_result.error_type}

        if tasks:
            siemplify.result.add_result_json([task.to_json() for task in tasks])

            siemplify.result.add_data_table(
                title="Created Defender ATP isolate machine tasks:",
                data_table=construct_csv([task.to_table() for task in tasks]),
            )

        output_message = "\n".join(output_messages)
        status = EXECUTION_STATE_COMPLETED

    except MicrosoftDefenderATPError as e:
        error = e
        output_message = f"Action didn't completed due to error: {e}"
        result = "false"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        error = e
        summary.log(EXECUTION_STATE_FAILED, error)
        raise

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    summary.log(status, error)

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
