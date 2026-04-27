from __future__ import annotations
import os
from typing import TYPE_CHECKING

from TIPCommon import extract_configuration_param, extract_action_param
from ..core.FreshworksFreshserviceManager import FreshworksFreshserviceManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import (
    INTEGRATION_IDENTIFIER,
    INTEGRATION_DISPLAY_NAME,
    CREATE_TICKET_SCRIPT_NAME,
    MEDIUM_PRIORITY,
    MEDIUM_URGENCY,
    MEDIUM_IMPACT,
    OPEN_TICKET,
    INCIDENT_TICKET,
    MAPPED_NUMERIC_TICKET_PRIORITIES,
    MAPPED_NUMERIC_TICKET_STATUSES,
    MAPPED_NUMERIC_TICKET_URGENCIES,
    MAPPED_NUMERIC_TICKET_IMPACTS,
    FILE_SIZE_LIMIT,
    SEPERATOR,
)
from ..core.datamodels import Department
from ..core.exceptions import (
    FreshworksFreshserviceValidationError,
    FreshworksFreshserviceMissingAgentError,
    FreshworksFreshserviceMissingGroupAgentError,
    FreshworksFreshserviceNonExistingFileError,
    FreshworksFreshserviceSizeLimitError,
)
from ..core.utils import (
    get_department_ids_by_names,
    load_csv_to_list,
    load_json_string_to_dict,
    remove_none_dictionary_values,
    string_to_multi_value,
)

if TYPE_CHECKING:
    from collections.abc import KeysView


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_IDENTIFIER} - {CREATE_TICKET_SCRIPT_NAME}"
    siemplify.LOGGER.info("=================== Main - Param Init ===================")

    # Integration configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Key",
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        default_value=True,
        print_value=True,
    )

    # Action configuration
    subject = extract_action_param(
        siemplify, param_name="Subject", print_value=True, is_mandatory=True
    )
    description = extract_action_param(
        siemplify, param_name="Description", print_value=True, is_mandatory=True
    )
    requester_email = extract_action_param(
        siemplify, param_name="Requester Email", print_value=True, is_mandatory=True
    )
    agent_assign_to = extract_action_param(
        siemplify, param_name="Agent Assign To", print_value=True
    )
    group_assign_to = extract_action_param(
        siemplify, param_name="Group Assign To", print_value=True
    )
    department_name = extract_action_param(
        siemplify,
        param_name="Department Name",
        print_value=True,
    )
    priority = extract_action_param(
        siemplify,
        param_name="Priority",
        print_value=True,
        default_value=MEDIUM_PRIORITY,
        is_mandatory=True,
    )
    urgency = extract_action_param(
        siemplify, param_name="Urgency", print_value=True, default_value=MEDIUM_URGENCY
    )
    impact = extract_action_param(
        siemplify, param_name="Impact", print_value=True, default_value=MEDIUM_IMPACT
    )
    tags = extract_action_param(siemplify, param_name="Tags", print_value=True)
    custom_fields = extract_action_param(
        siemplify, param_name="Custom Fields", print_value=True
    )
    attachments = string_to_multi_value(
        extract_action_param(
            siemplify, param_name="File Attachments to Add", print_value=True
        )
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    # Action results
    status = EXECUTION_STATE_COMPLETED
    result_value = False

    try:
        # Checking the existence of the attachments
        if attachments:
            non_existing_files = [
                path for path in attachments if not os.path.exists(path)
            ]
            if non_existing_files:
                all_separated_files = SEPERATOR.join(non_existing_files)
                raise FreshworksFreshserviceNonExistingFileError(
                    "Failed to create new ticket because the following"
                    "files were not found:"
                    f" \n{all_separated_files}"
                )
            else:
                total_size = 0
                for file in attachments:
                    total_size += os.path.getsize(file)
                    if total_size > FILE_SIZE_LIMIT:
                        raise FreshworksFreshserviceSizeLimitError(
                            "Failed to create new ticket because the total"
                            "size of the provided attachments exceeds 15 MB."
                        )

        tags = load_csv_to_list(tags, "Tags") if tags else None
        custom_fields = (
            load_json_string_to_dict(custom_fields, "Custom Fields")
            if custom_fields
            else None
        )
        manager = FreshworksFreshserviceManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
            force_test_connectivity=True,
        )

        responder_id, group_id = None, None

        # Lookup agent id
        if agent_assign_to:
            agent = manager.search_agent_by_attribute("email", agent_assign_to)
            if agent is None:
                raise FreshworksFreshserviceMissingAgentError(
                    "Failed to find agent assigned to the ticket"
                )
            responder_id = agent.agent_id

        # Lookup group id
        if group_assign_to:
            group = manager.search_agent_group_by_attribute("name", group_assign_to)
            if group is None:
                raise FreshworksFreshserviceMissingGroupAgentError(
                    "Failed to find group assigned to the ticket"
                )
            group_id = group.id

        department_id: int | None = None

        if department_name is not None:
            departments: list[Department] = manager.get_departments()
            department_ids_view: KeysView[int] = get_department_ids_by_names(
                departments,
                {department_name},
            )
            department_id = next(iter(department_ids_view))

        ticket = manager.create_ticket(
            **remove_none_dictionary_values(
                subject=subject,
                description=description,
                requester_email=requester_email,
                responder_id=responder_id,
                group_id=group_id,
                department_id=department_id,
                priority=MAPPED_NUMERIC_TICKET_PRIORITIES.get(priority),
                urgency=MAPPED_NUMERIC_TICKET_URGENCIES.get(urgency),
                impact=MAPPED_NUMERIC_TICKET_IMPACTS.get(impact),
                status=MAPPED_NUMERIC_TICKET_STATUSES.get(OPEN_TICKET),
                tags=tags,
                type=INCIDENT_TICKET,
                custom_fields=custom_fields,
                attachments=attachments,
            )
        )
        siemplify.result.add_result_json({"ticket": ticket.to_json()})
        output_message = f"New {INTEGRATION_DISPLAY_NAME} ticket created."
        result_value = True

    except (
        FreshworksFreshserviceMissingAgentError,
        FreshworksFreshserviceMissingGroupAgentError,
        FreshworksFreshserviceValidationError,
        FreshworksFreshserviceNonExistingFileError,
        FreshworksFreshserviceSizeLimitError,
    ) as error:
        output_message = f"Failed to create new ticket with the provided parameters! Error is: {error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    except Exception as error:
        output_message = (
            f'Error executing action "{CREATE_TICKET_SCRIPT_NAME}". Reason: {error}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
