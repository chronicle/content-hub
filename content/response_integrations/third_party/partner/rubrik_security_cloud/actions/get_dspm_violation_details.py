from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    GET_DSPM_VIOLATION_DETAILS_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import DSPMViolationDetails
from ..core.rubrik_exceptions import (
    GraphQLQueryException,
    ItemNotFoundException,
    RubrikException,
    UnauthorizedErrorException,
)
from ..core.utils import (
    format_authentication_failure_message,
    format_graphql_error_message,
    get_integration_params,
    validate_required_string,
    validate_uuid_format,
)


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_DSPM_VIOLATION_DETAILS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    json_results: list = []

    try:
        service_account_json, verify_ssl = get_integration_params(siemplify)

        violation_id = siemplify.extract_action_param(
            param_name="Violation ID",
            input_type=str,
            is_mandatory=True,
            print_value=True,
        )

        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        violation_id = validate_required_string(violation_id, "Violation ID")
        violation_id = validate_uuid_format(violation_id, "Violation ID")

        manager = APIManager(
            service_account_json,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        data = manager.get_dspm_violation_details(violation_id)
        json_results = [data]
        violation_raw = data.get("policyViolation", {})
        details_model = DSPMViolationDetails(violation_raw)

        table_data = [details_model.to_csv()]
        siemplify.result.add_data_table("DSPM Violation Details", construct_csv(table_data))

        output_message = (
            f"Successfully retrieved DSPM violation details for ID: {violation_id}. "
            f"Snapshot ID: {details_model.snapshot_id}. "
            f"Platform: {details_model.platform}. "
            f"Object Type: {details_model.object_type}."
        )
        siemplify.LOGGER.info(output_message)

    except (ItemNotFoundException, ValueError) as e:
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
        output_message = format_graphql_error_message(
            "API error during Get DSPM Violation Details", e
        )
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except RubrikException as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            GET_DSPM_VIOLATION_DETAILS_SCRIPT_NAME, e
        )
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            GET_DSPM_VIOLATION_DETAILS_SCRIPT_NAME, e
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
