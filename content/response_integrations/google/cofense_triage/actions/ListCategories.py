from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import construct_csv

from ..core.constants import INTEGRATION_NAME, LIST_CATEGORIES_ACTION
from ..core.CofenseTriageManager import CofenseTriageManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_CATEGORIES_ACTION
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

    names = extract_action_param(
        siemplify,
        param_name="Names",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )
    only_malicious = extract_action_param(
        siemplify,
        param_name="Only Malicious",
        default_value=False,
        is_mandatory=False,
        print_value=True,
        input_type=bool,
    )
    only_archived = extract_action_param(
        siemplify,
        param_name="Only Archived",
        default_value=False,
        is_mandatory=False,
        print_value=True,
        input_type=bool,
    )
    only_not_archived = extract_action_param(
        siemplify,
        param_name="Only Non Archived",
        default_value=False,
        is_mandatory=False,
        print_value=True,
        input_type=bool,
    )
    only_non_malicious = extract_action_param(
        siemplify,
        param_name="Only Non Malicious",
        default_value=False,
        is_mandatory=False,
        print_value=True,
        input_type=bool,
    )
    max_categories_to_return = extract_action_param(
        siemplify,
        param_name="Max Categories To Return",
        is_mandatory=False,
        default_value=20,
        print_value=True,
        input_type=int,
    )
    lower_score_to_fetch = extract_action_param(
        siemplify,
        param_name="Lowest Score To Fetch",
        is_mandatory=False,
        print_value=True,
        input_type=int,
    )

    output_message = ""
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    categories_table = []

    if names:
        max_categories_to_return = len(names)
        names = names.replace(" ", "")

    if (only_malicious and only_non_malicious) or (only_archived and only_not_archived):
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message += ("If parameters: Only Malicious or Only Archived are "
                           "checked, parameters Only Non Archived and Only Non "
                           "Malicious need to be unchecked, and vice-versa.")
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.info("----------------- Main - Finished -----------------")
        siemplify.LOGGER.info(
            f"\n  status: {status}\n  "
            f"result_value: {result_value}\n  "
            f"output_message: {output_message}"
        )
        siemplify.end(output_message, result_value, status)

    try:
        cofensetriage_manager = CofenseTriageManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
        )

        categories = cofensetriage_manager.get_categories(
            name=names,
            only_malicious=only_malicious,
            only_archived=only_archived,
            only_not_archived=only_not_archived,
            only_non_malicious=only_non_malicious,
            max_categories_to_return=max_categories_to_return,
            lower_score_to_fetch=lower_score_to_fetch,
        )

        if categories:
            siemplify.result.add_result_json(
                [related_object.to_json() for related_object in categories]
            )

            for report in categories:
                categories_table.append(report.to_table())

            siemplify.result.add_entity_table(
                "Available Categories", construct_csv(categories_table)
            )

            output_message += (
                f"Successfully returned available categories from {INTEGRATION_NAME}"
            )
        else:
            output_message += "No categories were found for the set criterias"

    except Exception as e:
        output_message += (
            f"Error executing action {LIST_CATEGORIES_ACTION}. Reason: {e}"
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
