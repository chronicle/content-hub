"""List Cases action for Abnormal Security Google SecOps SOAR Integration."""

from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.AbnormalManager import (
    AbnormalAuthenticationError,
    AbnormalConnectionError,
    AbnormalManager,
    AbnormalValidationError,
)
from ..core.constants import INTEGRATION_NAME, LIST_CASES_SCRIPT_NAME


@output_handler
def main() -> None:
    """Main execution logic for the List Cases action."""
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_CASES_SCRIPT_NAME
    siemplify.LOGGER.info(f"Action: {LIST_CASES_SCRIPT_NAME} started")

    api_url = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="API URL",
        is_mandatory=True,
        print_value=True,
    )
    api_key = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=True,
    )
    verify_ssl = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=False,
        default_value=True,
    )
    filter_str = siemplify.extract_action_param(
        param_name="Filter",
        is_mandatory=False,
        print_value=True,
    )
    page_size = int(
        siemplify.extract_action_param(
            param_name="Page Size",
            is_mandatory=False,
            default_value="100",
        )
        or 100
    )
    page_number = int(
        siemplify.extract_action_param(
            param_name="Page Number",
            is_mandatory=False,
            default_value="1",
        )
        or 1
    )

    result_value = False
    status = EXECUTION_STATE_FAILED
    try:
        manager = AbnormalManager(api_url=api_url, api_key=api_key, verify_ssl=verify_ssl)
        response = manager.list_cases(
            filter_str=filter_str or None,
            page_size=page_size,
            page_number=page_number,
        )
        cases = response.get("cases", [])
        siemplify.result.add_result_json(response)
        output_message = f"Retrieved {len(cases)} case(s)."
        result_value = True
        status = EXECUTION_STATE_COMPLETED

    except (
        AbnormalValidationError,
        AbnormalAuthenticationError,
        AbnormalConnectionError,
        Exception,
    ) as e:
        output_message = f'Error executing action "{LIST_CASES_SCRIPT_NAME}". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}  Result: {result_value}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
