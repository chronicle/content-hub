from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

from ..core.FreshworksFreshserviceManager import FreshworksFreshserviceManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import (
    INTEGRATION_IDENTIFIER,
    INTEGRATION_DISPLAY_NAME,
    LIST_AGENTS_SCRIPT_NAME,
    AGENT_STATE_ALL,
    ROWS_PER_PAGE_DEFAULT_VALUE,
    START_AT_PAGE_DEFAULT_VALUE,
    MAX_ROWS_TO_RETURN_DEFAULT_VALUE,
    LIST_AGENTS_TABLE_NAME,
    ROWS_PER_PAGE_PARAM_NAME,
    START_AT_PAGE_PARAM_NAME,
    MAX_ROWS_TO_RETURN_PARAM_NAME,
)
from ..core.exceptions import (
    FreshworksFreshserviceMissingAgentError,
    FreshworksFreshserviceValidationError,
)
from ..core.utils import (
    update_department_names,
    update_record_location_name,
    update_agent_group_names,
    update_agent_roles_names,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_IDENTIFIER} - {LIST_AGENTS_SCRIPT_NAME}"
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
    agent_email = extract_action_param(
        siemplify, param_name="Agent Email", print_value=True, is_mandatory=False
    )
    agent_state = extract_action_param(
        siemplify,
        param_name="Agent State",
        print_value=True,
        is_mandatory=False,
        default_value=AGENT_STATE_ALL,
    )
    include_not_active_agents = extract_action_param(
        siemplify,
        param_name="Include not Active Agents",
        print_value=True,
        is_mandatory=False,
        default_value=False,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    # Action results
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        rows_per_page = extract_action_param(
            siemplify,
            param_name=ROWS_PER_PAGE_PARAM_NAME,
            print_value=True,
            is_mandatory=False,
            default_value=ROWS_PER_PAGE_DEFAULT_VALUE,
            input_type=int,
        )
        start_at_page = extract_action_param(
            siemplify,
            param_name=START_AT_PAGE_PARAM_NAME,
            print_value=True,
            is_mandatory=False,
            default_value=START_AT_PAGE_DEFAULT_VALUE,
            input_type=int,
        )
        max_rows_to_return = extract_action_param(
            siemplify,
            param_name=MAX_ROWS_TO_RETURN_PARAM_NAME,
            print_value=True,
            is_mandatory=False,
            default_value=MAX_ROWS_TO_RETURN_DEFAULT_VALUE,
            input_type=int,
        )

        if rows_per_page <= 0:
            raise FreshworksFreshserviceValidationError(
                f'"{ROWS_PER_PAGE_PARAM_NAME}" parameter provided must be positive.'
            )
        if start_at_page <= 0:
            raise FreshworksFreshserviceValidationError(
                f'"{START_AT_PAGE_PARAM_NAME}" parameter provided must be positive.'
            )
        if max_rows_to_return <= 0:
            raise FreshworksFreshserviceValidationError(
                f"'{MAX_ROWS_TO_RETURN_PARAM_NAME}'"
                " parameter provided must be positive."
            )

        manager = FreshworksFreshserviceManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        siemplify.LOGGER.info(f"Fetching agents from {INTEGRATION_DISPLAY_NAME}")
        agents = manager.get_filtered_agents(
            agent_email=agent_email,
            agent_state=agent_state.lower(),
            include_not_active_agents=include_not_active_agents,
            rows_per_page=rows_per_page,
            start_at_page=start_at_page,
            max_rows_to_return=max_rows_to_return,
        )

        if not agents:
            raise FreshworksFreshserviceMissingAgentError

        siemplify.LOGGER.info(
            f"Successfully fetched agents from {INTEGRATION_DISPLAY_NAME}"
        )

        siemplify.LOGGER.info(f"Fetching Agent groups from {INTEGRATION_DISPLAY_NAME}")
        agent_groups = manager.get_agent_groups()
        siemplify.LOGGER.info(
            f"Successfully fetched agents groups from {INTEGRATION_DISPLAY_NAME}"
        )

        siemplify.LOGGER.info(f"Fetching departments from {INTEGRATION_DISPLAY_NAME}")
        departments = manager.get_departments()
        siemplify.LOGGER.info(
            f"Successfully fetched departments from {INTEGRATION_DISPLAY_NAME}"
        )

        siemplify.LOGGER.info(f"Fetching locations from {INTEGRATION_DISPLAY_NAME}")
        locations = manager.get_locations()
        siemplify.LOGGER.info(
            f"Successfully fetched locations from {INTEGRATION_DISPLAY_NAME}"
        )

        siemplify.LOGGER.info(f"Fetching agent roles from {INTEGRATION_DISPLAY_NAME}")
        agent_roles = manager.get_agent_roles()
        siemplify.LOGGER.info(
            f"Successfully fetched agent roles from {INTEGRATION_DISPLAY_NAME}"
        )

        for agent in agents:
            update_department_names(agent, departments)
            update_record_location_name(agent, locations)
            update_agent_group_names(agent, agent_groups)
            update_agent_roles_names(agent, agent_roles)

        json_results_list = [agent.to_json() for agent in agents]
        siemplify.result.add_result_json({"agents": json_results_list})

        siemplify.result.add_data_table(
            title=LIST_AGENTS_TABLE_NAME,
            data_table=construct_csv([agent.as_csv() for agent in agents]),
        )

        output_message = f"Successfully fetched {INTEGRATION_DISPLAY_NAME} agents."

    except FreshworksFreshserviceValidationError as e:
        output_message = (
            f"Failed to list agents with the provided parameters! Error is: {e}"
        )
        siemplify.LOGGER.error(output_message)
        result_value = False
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_COMPLETED

    except FreshworksFreshserviceMissingAgentError as e:
        output_message = "No agents were found for the provided input parameters."
        siemplify.LOGGER.error(output_message)
        result_value = False
        status = EXECUTION_STATE_COMPLETED

    except Exception as error:
        result_value = False
        output_message = (
            f'Error executing action "{LIST_AGENTS_SCRIPT_NAME}". Reason: {error}'
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
