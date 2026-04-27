from __future__ import annotations
import json

from ..core.FreshworksFreshserviceManager import FreshworksFreshserviceManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.consts import (
    INTEGRATION_IDENTIFIER,
    INTEGRATION_DISPLAY_NAME,
    CREATE_AGENT_SCRIPT_NAME,
)
from ..core.exceptions import FreshworksFreshserviceValidationError
from ..core.utils import (
    load_csv_to_list,
    load_json_string_to_dict,
    remove_none_dictionary_values,
    get_group_ids_by_names,
    get_department_ids_by_names,
    get_location_id_by_name,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_IDENTIFIER} - {CREATE_AGENT_SCRIPT_NAME}"
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
    email = extract_action_param(
        siemplify, param_name="Email", print_value=True, is_mandatory=True
    )
    first_name = extract_action_param(
        siemplify, param_name="First Name", print_value=True, is_mandatory=True
    )
    last_name = extract_action_param(
        siemplify, param_name="Last Name", print_value=True, is_mandatory=False
    )
    is_occasional = extract_action_param(
        siemplify,
        param_name="Is occasional",
        print_value=True,
        input_type=bool,
        is_mandatory=False,
        default_value=False,
    )
    can_see_all_tickets_from_associated_departments = extract_action_param(
        siemplify,
        param_name="Can See All Tickets From Associated Departments",
        print_value=True,
        input_type=bool,
        is_mandatory=False,
        default_value=False,
    )
    department_names = extract_action_param(
        siemplify, param_name="Departments", print_value=True, is_mandatory=False
    )
    location = extract_action_param(
        siemplify, param_name="Location", print_value=True, is_mandatory=False
    )
    group_membership = extract_action_param(
        siemplify, param_name="Group Memberships", print_value=True, is_mandatory=False
    )
    roles = extract_action_param(
        siemplify, param_name="Roles", print_value=True, is_mandatory=True
    )
    job_title = extract_action_param(
        siemplify, param_name="Job Title", print_value=True, is_mandatory=False
    )
    custom_fields = extract_action_param(
        siemplify, param_name="Custom Fields", print_value=True, is_mandatory=False
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    # Action results
    status = EXECUTION_STATE_COMPLETED
    result_value = False

    try:
        department_names_list = (
            load_csv_to_list(department_names, "Departments")
            if department_names
            else None
        )
        group_membership_list = (
            load_csv_to_list(group_membership, "Group Membership")
            if group_membership
            else None
        )
        custom_fields = (
            load_json_string_to_dict(custom_fields, "Custom Fields")
            if custom_fields
            else None
        )

        try:
            roles_dict = json.loads(roles)

        except Exception as error:
            raise FreshworksFreshserviceValidationError(
                "Roles parameter is invalid. Please read parameter description"
                "for more details."
            )

        manager = FreshworksFreshserviceManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        agent_group_ids = None
        if group_membership_list:
            siemplify.LOGGER.info(
                f"Fetching Agent groups from {INTEGRATION_DISPLAY_NAME}"
            )
            agent_groups = manager.get_agent_groups()
            siemplify.LOGGER.info(
                f"Successfully fetched agents groups from {INTEGRATION_DISPLAY_NAME}"
            )
            agent_group_ids = get_group_ids_by_names(
                agent_groups, set(group_membership_list)
            )
            siemplify.LOGGER.info(
                "Successfully found agent groups ids of the provided group names"
            )

        department_ids = None
        if department_names_list:
            siemplify.LOGGER.info(
                f"Fetching departments from {INTEGRATION_DISPLAY_NAME}"
            )
            departments = manager.get_departments()
            siemplify.LOGGER.info(
                f"Successfully fetched departments from {INTEGRATION_DISPLAY_NAME}"
            )
            department_ids = get_department_ids_by_names(
                departments, set(department_names_list)
            )
            siemplify.LOGGER.info(
                "Successfully found departments ids of the provided departments names"
            )

        location_id = None
        if location:
            siemplify.LOGGER.info(f"Fetching locations from {INTEGRATION_DISPLAY_NAME}")
            locations = manager.get_locations()
            siemplify.LOGGER.info(
                f"Successfully fetched locations from {INTEGRATION_DISPLAY_NAME}"
            )
            location_id = get_location_id_by_name(locations, location)
            siemplify.LOGGER.info(
                "Successfully found location id of the provided location name"
            )

        agent = manager.create_agent(
            **remove_none_dictionary_values(
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_occasional=is_occasional,
                can_see_all_tickets_from_associated_departments=
                can_see_all_tickets_from_associated_departments,
                department_ids=list(department_ids) if department_ids else None,
                location_id=location_id,
                member_of=list(agent_group_ids) if agent_group_ids else None,
                roles=roles_dict,
                job_title=job_title,
                custom_fields=custom_fields,
            )
        )
        siemplify.result.add_result_json(agent.to_json())
        output_message = f"New {INTEGRATION_DISPLAY_NAME} agent created."
        result_value = True

    except FreshworksFreshserviceValidationError as error:
        output_message = f"Failed to create new agent with the provided parameters! Error is: {error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    except Exception as error:
        output_message = (
            f'Error executing action "{CREATE_AGENT_SCRIPT_NAME}". Reason: {error}'
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
