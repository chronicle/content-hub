from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.GoogleChatManager import GoogleChatManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import (
    INTEGRATION_NAME,
    LIST_SPACES_SCRIPT_NAME,
    DEFAULT_LIMIT,
    FILTER_KEY_MAPPING,
    PRODUCT,
)
from ..core.utils import validate_positive_integer
import copy


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_SPACES_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root URL",
        is_mandatory=True,
    )
    service_account = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Service Account"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        print_value=True,
        input_type=bool,
    )

    filter_key = extract_action_param(
        siemplify, param_name="Filter Key", print_value=True
    )
    filter_logic = extract_action_param(
        siemplify, param_name="Filter Logic", print_value=True
    )
    filter_value = extract_action_param(
        siemplify, param_name="Filter Value", print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Records To Return",
        input_type=int,
        default_value=DEFAULT_LIMIT,
        print_value=True,
    )
    fetch_membership = extract_action_param(
        siemplify,
        param_name="Include User Memberships",
        input_type=bool,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    json_results, csv_result = [], []
    output_message = (
        f"Successfully found added spaces for the provided criteria in {PRODUCT}."
    )
    result_value = True

    try:
        validate_positive_integer(
            number=limit,
            err_msg=f'Invalid value was provided for "Max Records to Return": {limit}. '
            f"Positive number should be provided",
        )

        if filter_logic and not filter_key:
            raise ValueError(
                'you need to select a field from the "Filter Key" parameter.'
            )

        manager = GoogleChatManager(
            api_root=api_root,
            service_account_string=service_account,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        spaces = manager.list_spaces(
            filter_key=FILTER_KEY_MAPPING[filter_key],
            filter_logic=filter_logic,
            filter_value=filter_value,
            limit=limit,
        )

        for space in spaces:
            space_json = space.to_json()
            space_csv = space.to_csv()
            if fetch_membership:
                memberships = manager.fetch_space_membership(space_name=space.name)
                space_json["memberships"] = [
                    membership.to_json() for membership in memberships
                ]
                for member in memberships:
                    csv_with_member = copy.deepcopy(space_csv)
                    csv_with_member["Member Display Name"] = member.display_name
                    csv_result.append(csv_with_member)
            else:
                csv_result.append(space_csv)

            json_results.append(space_json)

        if spaces:
            siemplify.result.add_data_table(
                title="Available Spaces Bot was Added to",
                data_table=construct_csv(list(csv_result)),
            )
            siemplify.result.add_result_json(json_results)
            if not filter_value:
                output_message += '\nThe filter was not applied, because parameter \
                    "Filter Value" has an empty value.'
        else:
            result_value = False
            output_message = (
                f"No spaces were found for the provided criteria in {PRODUCT}"
            )

    except Exception as e:
        output_message = (
            f'Error executing action "{LIST_SPACES_SCRIPT_NAME}". Reason: {e}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
