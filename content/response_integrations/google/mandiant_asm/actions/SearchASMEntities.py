from __future__ import annotations
from ..core.MandiantASMManager import MandiantASMManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    string_to_multi_value,
    unix_now,
)
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    SEARCH_ASM_ENTITIES_SCRIPT_NAME,
    MAX_SEARCH_ENTITIES_LIMIT,
)

DEFAULT_SEARCH_ENTITIES_LIMIT = 50


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SEARCH_ASM_ENTITIES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    action_start_time = unix_now()

    # Integration parameters
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    access_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Access Key",
        remove_whitespaces=False,
    )
    secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Secret Key",
        remove_whitespaces=False,
    )
    gti_api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="GTI API Key",
        remove_whitespaces=False,
    )
    project_name = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Project Name"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    # Action parameters
    entity_name = string_to_multi_value(
        extract_action_param(
            siemplify, param_name="Entity Name", print_value=True, input_type=str
        )
    )
    tags = string_to_multi_value(
        extract_action_param(
            siemplify, param_name="Tags", print_value=True, input_type=str
        )
    )
    critical_or_high = extract_action_param(
        siemplify,
        param_name="Critical or High Issue",
        print_value=True,
        input_type=bool,
    )
    vuln_count_gte = extract_action_param(
        siemplify,
        param_name="Minimum Vulnerabilities Count",
        print_value=True,
        input_type=str,
    )
    issue_count_gte = extract_action_param(
        siemplify, param_name="Minimum Issues Count", print_value=True, input_type=str
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Entities To Return",
        print_value=True,
        input_type=int,
        default_value=DEFAULT_SEARCH_ENTITIES_LIMIT,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    action_status = EXECUTION_STATE_COMPLETED
    output_message = f"No entities were found based on the provided criteria in {INTEGRATION_DISPLAY_NAME}."

    try:
        try:
            limit = int(limit)
            if limit <= 0:
                raise ValueError
            if limit >= MAX_SEARCH_ENTITIES_LIMIT:
                siemplify.LOGGER.info(
                    f'Provided "Max Entities To Return" value is greater than allowed maximum, '
                    f"{MAX_SEARCH_ENTITIES_LIMIT} will be used instead"
                )
                limit = MAX_SEARCH_ENTITIES_LIMIT
        except ValueError:
            raise ValueError("Max Entities To Return must be a positive integer")
        if vuln_count_gte:
            try:
                vuln_count_gte = int(vuln_count_gte)
                if vuln_count_gte <= 0:
                    raise ValueError
            except ValueError:
                raise ValueError(
                    "Minimum Vulnerabilities Count must be a positive integer"
                )
        if issue_count_gte:
            try:
                issue_count_gte = int(issue_count_gte)
                if issue_count_gte <= 0:
                    raise ValueError
            except ValueError:
                raise ValueError("Minimum Issues Count must be a positive integer")

        manager = MandiantASMManager(
            api_root=api_root,
            access_key=access_key,
            secret_key=secret_key,
            gti_api_key=gti_api_key,
            project_name=project_name,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        entities = manager.search_asm_entities(
            entity_name=entity_name,
            tags=tags,
            critical_or_high=critical_or_high,
            limit=limit,
            script_starting_time=action_start_time,
            execution_deadline=siemplify.execution_deadline_unix_time_ms,
            vuln_count_gte=vuln_count_gte,
            issue_count_gte=issue_count_gte,
        )

        if entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(
                    {entity.name: entity.to_json() for entity in entities}
                )
            )
            result_value = True
            output_message = (
                f"Successfully returned entities based on the "
                f"provided criteria in {INTEGRATION_DISPLAY_NAME}."
            )

    except Exception as e:
        result_value = False
        action_status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {SEARCH_ASM_ENTITIES_SCRIPT_NAME}. Error is {e}"
        )
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {action_status}"
        f"\n  is_success: {result_value}"
        f"\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, action_status)


if __name__ == "__main__":
    main()
