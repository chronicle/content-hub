from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    DEFAULT_FILE_LIST_MAX_RESULTS,
    ERROR_CREATION_DATE_ORDER,
    ERROR_LAST_ACCESS_DATE_ORDER,
    ERROR_LAST_SCAN_DATE_ORDER,
    ERROR_LAST_UPDATED_DATE_ORDER,
    GET_VIOLATION_FILE_LIST_SCRIPT_NAME,
    MAX_FILES,
    MAX_TABLE_RECORDS,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import FileEntry
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
    parse_file_access_via_param,
    parse_file_exposure_param,
    parse_file_risk_level_param,
    parse_file_sort_by_param,
    parse_sort_order_param,
    validate_date_order,
    validate_date_pair_required,
    validate_iso_datetime,
    validate_max_results,
    validate_required_string,
    validate_uuid_format,
)


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_VIOLATION_FILE_LIST_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    json_results: list = []

    try:
        service_account_json, verify_ssl = get_integration_params(siemplify)

        object_id = siemplify.extract_action_param(
            param_name="Object ID",
            input_type=str,
            is_mandatory=True,
            print_value=True,
        )
        violation_id = siemplify.extract_action_param(
            param_name="Violation ID",
            input_type=str,
            is_mandatory=False,
            print_value=True,
        )
        snapshot_id = siemplify.extract_action_param(
            param_name="Snapshot ID",
            input_type=str,
            is_mandatory=True,
            print_value=True,
        )
        file_name_filter = siemplify.extract_action_param(
            param_name="File Name Filter",
            input_type=str,
            is_mandatory=False,
            print_value=True,
        )
        risk_levels = parse_file_risk_level_param(siemplify)
        exposure_filter = parse_file_exposure_param(siemplify)
        access_via = parse_file_access_via_param(siemplify)
        sort_by = parse_file_sort_by_param(siemplify, default="HITS")
        sort_order = parse_sort_order_param(siemplify, default="DESC")

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

        last_access_start = siemplify.extract_action_param(
            param_name="Last Access Start Date", input_type=str, is_mandatory=False, print_value=True
        )
        last_access_end = siemplify.extract_action_param(
            param_name="Last Access End Date", input_type=str, is_mandatory=False, print_value=True
        )
        last_updated_start = siemplify.extract_action_param(
            param_name="Last Updated Start Date", input_type=str, is_mandatory=False, print_value=True
        )
        last_updated_end = siemplify.extract_action_param(
            param_name="Last Updated End Date", input_type=str, is_mandatory=False, print_value=True
        )
        creation_start = siemplify.extract_action_param(
            param_name="Creation Start Date", input_type=str, is_mandatory=False, print_value=True
        )
        creation_end = siemplify.extract_action_param(
            param_name="Creation End Date", input_type=str, is_mandatory=False, print_value=True
        )
        last_scan_start = siemplify.extract_action_param(
            param_name="Last Scan Start Date", input_type=str, is_mandatory=False, print_value=True
        )
        last_scan_end = siemplify.extract_action_param(
            param_name="Last Scan End Date", input_type=str, is_mandatory=False, print_value=True
        )

        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        object_id = validate_uuid_format(
            validate_required_string(object_id, "Object ID"), "Object ID"
        )
        snapshot_id = validate_uuid_format(
            validate_required_string(snapshot_id, "Snapshot ID"), "Snapshot ID"
        )
        # Violation ID is optional; validate its format only when provided and omit
        # it from the filter otherwise (handled in get_violation_file_list).
        violation_id = violation_id.strip() if violation_id else ""
        if violation_id:
            violation_id = validate_uuid_format(violation_id, "Violation ID")

        last_access_start = validate_iso_datetime(last_access_start, "Last Access Start Date")
        last_access_end = validate_iso_datetime(last_access_end, "Last Access End Date")
        last_updated_start = validate_iso_datetime(last_updated_start, "Last Updated Start Date")
        last_updated_end = validate_iso_datetime(last_updated_end, "Last Updated End Date")
        creation_start = validate_iso_datetime(creation_start, "Creation Start Date")
        creation_end = validate_iso_datetime(creation_end, "Creation End Date")
        last_scan_start = validate_iso_datetime(last_scan_start, "Last Scan Start Date")
        last_scan_end = validate_iso_datetime(last_scan_end, "Last Scan End Date")

        validate_date_pair_required(
            last_access_start, last_access_end, "Last Access Start Date", "Last Access End Date"
        )
        validate_date_pair_required(
            last_updated_start, last_updated_end, "Last Updated Start Date", "Last Updated End Date"
        )
        validate_date_pair_required(
            creation_start, creation_end, "Creation Start Date", "Creation End Date"
        )
        validate_date_pair_required(
            last_scan_start, last_scan_end, "Last Scan Start Date", "Last Scan End Date"
        )

        validate_date_order(last_access_start, last_access_end, ERROR_LAST_ACCESS_DATE_ORDER)
        validate_date_order(last_updated_start, last_updated_end, ERROR_LAST_UPDATED_DATE_ORDER)
        validate_date_order(creation_start, creation_end, ERROR_CREATION_DATE_ORDER)
        validate_date_order(last_scan_start, last_scan_end, ERROR_LAST_SCAN_DATE_ORDER)

        max_results = validate_max_results(
            max_results_raw,
            default=DEFAULT_FILE_LIST_MAX_RESULTS,
            max_allowed=MAX_FILES,
        )

        manager = APIManager(
            service_account_json,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        data = manager.get_violation_file_list(
            snappable_fid=object_id,
            snapshot_fid=snapshot_id,
            violation_id=violation_id or None,
            filename_filter=file_name_filter or None,
            risk_levels=risk_levels,
            exposures=exposure_filter,
            access_via=access_via,
            last_access_start=last_access_start,
            last_access_end=last_access_end,
            last_updated_start=last_updated_start,
            last_updated_end=last_updated_end,
            creation_start=creation_start,
            creation_end=creation_end,
            last_scan_start=last_scan_start,
            last_scan_end=last_scan_end,
            sort_by=sort_by,
            sort_order=sort_order,
            first=max_results,
            after_cursor=next_page_token or None,
        )

        policy_obj = data.get("policyObj") or {}
        file_connection = policy_obj.get("fileResultConnection") or {}
        edges = file_connection.get("edges") or []
        nodes = [edge.get("node", {}) for edge in edges if edge.get("node")]
        page_info = file_connection.get("pageInfo") or {}
        has_next_page = page_info.get("hasNextPage", False)
        end_cursor = page_info.get("endCursor")

        if not nodes:
            output_message = "No files found matching the applied filters."
        else:
            json_results = nodes
            file_models = [FileEntry(node) for node in nodes]
            table_data = [f.to_csv() for f in file_models]
            table_data = table_data[:MAX_TABLE_RECORDS]
            siemplify.result.add_data_table(
                "Violation Files", construct_csv(table_data)
            )
            output_message = (
                f"Successfully retrieved {len(nodes)} file(s) for violation ID: {violation_id}."
            )
            if has_next_page and end_cursor:
                output_message += (
                    f" Use Next Page Token '{end_cursor}' to retrieve the next page."
                )
            siemplify.LOGGER.info(
                "Note: SHA1 hash is not returned by this action. For NTFS quarantine "
                "flows, SHA1 must be resolved via Defender ATP Advanced Hunting query."
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
        output_message = format_graphql_error_message("API error during Get Violation File List", e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except RubrikException as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            GET_VIOLATION_FILE_LIST_SCRIPT_NAME, e
        )
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            GET_VIOLATION_FILE_LIST_SCRIPT_NAME, e
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

if __name__ == "__main__":
    main()
