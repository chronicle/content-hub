from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.SumoLogicCloudSIEMManager import SumoLogicCloudSIEMManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    UPDATE_INSIGHT_SCRIPT_NAME,
    STATUS_MAPPING,
    ASSIGNEE_TYPE_MAPPING,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_INSIGHT_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="API Key"
    )
    access_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Access ID",
        print_value=True,
    )
    access_key = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Access Key"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    # action parameters
    insight_id = extract_action_param(
        siemplify, param_name="Insight ID", is_mandatory=True, print_value=True
    )
    insight_status = extract_action_param(
        siemplify, param_name="Status", is_mandatory=True, print_value=True
    )
    assignee_type = extract_action_param(
        siemplify, param_name="Assignee Type", is_mandatory=True, print_value=True
    )
    assignee = extract_action_param(siemplify, param_name="Assignee", print_value=True)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = True
    status = EXECUTION_STATE_COMPLETED

    try:
        if not STATUS_MAPPING.get(insight_status) and not assignee:
            raise Exception("either status or assignee needs to be provided")

        manager = SumoLogicCloudSIEMManager(
            api_root=api_root,
            api_key=api_key,
            access_id=access_id,
            access_key=access_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        if assignee:
            manager.update_assignee(
                insight_id, ASSIGNEE_TYPE_MAPPING.get(assignee_type), assignee
            )
        if STATUS_MAPPING.get(insight_status):
            manager.update_status(insight_id, STATUS_MAPPING.get(insight_status))

        insight = manager.get_insight(insight_id)
        siemplify.result.add_result_json(insight.to_json())
        output_message = f'Successfully updated insight with ID "{insight_id}" in {INTEGRATION_DISPLAY_NAME}.'

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {UPDATE_INSIGHT_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {UPDATE_INSIGHT_SCRIPT_NAME}. Reason: {e}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
