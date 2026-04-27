from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.constants import ADD_TAGS_TO_REPORT_ACTION, INTEGRATION_NAME
from ..core.CofenseTriageExceptions import RecordNotFoundException
from ..core.CofenseTriageManager import CofenseTriageManager

from TIPCommon.extraction import extract_action_param, extract_configuration_param


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_TAGS_TO_REPORT_ACTION
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        print_value=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    report_id = extract_action_param(
        siemplify,
        param_name="Report ID",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )
    tags = extract_action_param(
        siemplify,
        param_name="Tags",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    output_message = ""
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:

        tags = [tag.strip() for tag in tags.split(",") if tag.strip()]

        cofensetriage_manager = CofenseTriageManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
        )
        current_tags = cofensetriage_manager.get_report_tags(report_id)

        new_tags = list(set(current_tags.tags + tags))
        cofensetriage_manager.update_report(report_id, new_tags)
        report = cofensetriage_manager.get_report(report_id)

        siemplify.result.add_result_json(report.to_json())
        output_message += (f"Successfully added tags to the the report with ID "
                           f"{report_id} in {INTEGRATION_NAME}.")

    except RecordNotFoundException as e:
        output_message += (f"Action wasn't able to add tags to the report with ID "
                           f"{report_id} in {ADD_TAGS_TO_REPORT_ACTION}. Reason:\n {e}")
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False

    except Exception as e:
        output_message += (
            f"Error executing action {ADD_TAGS_TO_REPORT_ACTION}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  "
        f"result_value: {result_value}\n  "
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
