from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.VMRayClientManager import VMRayClient
from ..core.constants import INTEGRATION_NAME, ADD_TAG_TO_SUBMISSION_SCRIPT_NAME
from ..core.UtilsManager import get_system_versions


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_TAG_TO_SUBMISSION_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # integration configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Key"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    # action parameters
    submission_id = extract_action_param(
        siemplify,
        param_name="Submission ID",
        is_mandatory=True,
        print_value=True,
        input_type=int,
    )
    tag_name = extract_action_param(
        siemplify, param_name="Tag Name", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        vmray_manager = VMRayClient(
            api_root, api_key, verify_ssl, **get_system_versions(siemplify)
        )
        vmray_manager.add_tag_to_submission(submission_id, tag_name)
        status = EXECUTION_STATE_COMPLETED
        result_value = True
        output_message = (
            f"Successfully added tag {tag_name} to submission {submission_id}"
        )
        siemplify.LOGGER.info("Finished processing")

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {ADD_TAG_TO_SUBMISSION_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = (
            f"Failed to add tag {tag_name} to submission {submission_id}. Error is {e}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
