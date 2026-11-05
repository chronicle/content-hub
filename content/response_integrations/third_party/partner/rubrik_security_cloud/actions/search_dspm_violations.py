from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    DEFAULT_MAX_RESULTS,
    ERROR_DETECTION_DATE_ORDER,
    ERROR_MAX_RESULTS_NOT_INTEGER,
    ERROR_MAX_RESULTS_TOO_HIGH,
    ERROR_MAX_RESULTS_TOO_LOW,
    ERROR_UPDATE_DATE_ORDER,
    MAX_TABLE_RECORDS,
    MAX_VIOLATIONS,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
    SEARCH_DSPM_VIOLATIONS_SCRIPT_NAME,
)
from ..core.datamodels import DSPMViolation
from ..core.rubrik_exceptions import (
    GraphQLQueryException,
    InvalidIntegerException,
    InvalidValueException,
    RubrikException,
    UnauthorizedErrorException,
)
from ..core.utils import (
    format_authentication_failure_message,
    format_graphql_error_message,
    get_integration_params,
    parse_dspm_category_param,
    parse_dspm_object_type_param,
    parse_dspm_severity_param,
    parse_dspm_sort_by_param,
    parse_sensitivity_level_param,
    parse_sort_order_param,
    parse_status_param,
    validate_date_order,
    validate_date_pair_required,
    validate_iso_datetime,
)


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = SEARCH_DSPM_VIOLATIONS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    json_results: list = []

    try:
        service_account_json, verify_ssl = get_integration_params(siemplify)

        object_types = parse_dspm_object_type_param(siemplify)
        statuses = parse_status_param(siemplify)
        severities = parse_dspm_severity_param(siemplify)
        categories = parse_dspm_category_param(siemplify)
        sensitivity_levels = parse_sensitivity_level_param(siemplify)

        detection_start_date = siemplify.extract_action_param(
            param_name="Detection Start Date",
            input_type=str,
            is_mandatory=False,
            print_value=True,
        )
        detection_end_date = siemplify.extract_action_param(
            param_name="Detection End Date",
            input_type=str,
            is_mandatory=False,
            print_value=True,
        )
        update_start_date = siemplify.extract_action_param(
            param_name="Update Start Date",
            input_type=str,
            is_mandatory=False,
            print_value=True,
        )
        update_end_date = siemplify.extract_action_param(
            param_name="Update End Date",
            input_type=str,
            is_mandatory=False,
            print_value=True,
        )
        sort_by = parse_dspm_sort_by_param(siemplify)
        sort_order = parse_sort_order_param(siemplify)

        max_results_raw = siemplify.extract_action_param(
            param_name="Max Results",
            input_type=str,
            is_mandatory=False,
            print_value=True,
        )
        next_page_token = siemplify.extract_action_param(
            param_name="Next Page Token",
            input_type=str,
            is_mandatory=False,
            print_value=True,
        )

        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        detection_start_date = validate_iso_datetime(detection_start_date, "Detection Start Date")
        detection_end_date = validate_iso_datetime(detection_end_date, "Detection End Date")
        update_start_date = validate_iso_datetime(update_start_date, "Update Start Date")
        update_end_date = validate_iso_datetime(update_end_date, "Update End Date")

        validate_date_pair_required(
            detection_start_date, detection_end_date, "Detection Start Date", "Detection End Date"
        )
        validate_date_pair_required(
            update_start_date, update_end_date, "Update Start Date", "Update End Date"
        )

        validate_date_order(detection_start_date, detection_end_date, ERROR_DETECTION_DATE_ORDER)
        validate_date_order(update_start_date, update_end_date, ERROR_UPDATE_DATE_ORDER)

        max_results = validate_max_results(max_results_raw)

        manager = APIManager(
            service_account_json,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        data = manager.search_dspm_violations(
            statuses=statuses,
            severities=severities,
            categories=categories,
            sensitivity_levels=sensitivity_levels,
            object_types=object_types,
            start_date=detection_start_date or None,
            end_date=detection_end_date or None,
            update_start_date=update_start_date or None,
            update_end_date=update_end_date or None,
            sort_by=sort_by,
            sort_order=sort_order,
            first=max_results,
            after_cursor=next_page_token or None,
        )

        policy_violations = data.get("policyViolations") or {}
        total_count = policy_violations.get("count", 0)
        edges = policy_violations.get("edges") or []
        nodes = [edge.get("node", {}) for edge in edges if edge.get("node")]
        page_info = policy_violations.get("pageInfo") or {}
        has_next_page = page_info.get("hasNextPage", False)
        end_cursor = page_info.get("endCursor")

        if not nodes:
            output_message = "No DSPM violations found matching the applied filters."
        else:
            json_results = nodes
            violation_models = [DSPMViolation(node) for node in nodes]
            table_data = [v.to_csv() for v in violation_models]
            table_data = table_data[:MAX_TABLE_RECORDS]
            siemplify.result.add_data_table(
                "DSPM Violations", construct_csv(table_data)
            )
            output_message = (
                f"Successfully retrieved {len(nodes)} DSPM violation(s) "
                f"(total matching: {total_count})."
            )
            if has_next_page and end_cursor:
                output_message += (
                    f" Use Next Page Token '{end_cursor}' to retrieve the next page."
                )

        siemplify.LOGGER.info(output_message)

    except (InvalidValueException, InvalidIntegerException) as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)

    except UnauthorizedErrorException as e:
        output_message = format_authentication_failure_message(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except GraphQLQueryException as e:
        output_message = format_graphql_error_message("API error during Search DSPM Violations", e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except RubrikException as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            SEARCH_DSPM_VIOLATIONS_SCRIPT_NAME, e
        )
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            SEARCH_DSPM_VIOLATIONS_SCRIPT_NAME, e
        )
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    finally:
        siemplify.result.add_result_json(json_results)
        siemplify.LOGGER.info("----------------- Main - Finished -----------------")
        siemplify.LOGGER.info(f"Status: {status}")
        siemplify.LOGGER.info(f"result_value: {result_value}")
        siemplify.LOGGER.info(f"Output Message: {output_message}")
        siemplify.end(output_message, result_value, status)


def validate_max_results(raw_value) -> int:
    """Validate the Max Results parameter per the Search DSPM Violations spec.

    Raises:
        InvalidIntegerException: With the exact wording required by the action's
            case wall output message contract.
    """
    if raw_value is None or not str(raw_value).strip():
        return DEFAULT_MAX_RESULTS

    raw_value = str(raw_value).strip()
    try:
        value = int(raw_value)
    except ValueError:
        raise InvalidIntegerException(ERROR_MAX_RESULTS_NOT_INTEGER.format(raw_value))

    if value < 1:
        raise InvalidIntegerException(ERROR_MAX_RESULTS_TOO_LOW)
    if value > MAX_VIOLATIONS:
        raise InvalidIntegerException(ERROR_MAX_RESULTS_TOO_HIGH.format(MAX_VIOLATIONS, raw_value))

    return value


if __name__ == "__main__":
    main()
