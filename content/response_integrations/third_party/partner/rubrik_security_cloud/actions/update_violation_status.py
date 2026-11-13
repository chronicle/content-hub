from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
    STATUS_ENUM_MAP,
    UPDATE_VIOLATION_STATUS_SCRIPT_NAME,
)
from ..core.rubrik_exceptions import (
    GraphQLQueryException,
    InvalidValueException,
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
    siemplify.script_name = UPDATE_VIOLATION_STATUS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    json_results: dict = {}

    try:
        service_account_json, verify_ssl = get_integration_params(siemplify)

        violation_id = siemplify.extract_action_param(
            param_name="Violation ID",
            input_type=str,
            is_mandatory=True,
            print_value=True,
        )
        new_status_label = siemplify.extract_action_param(
            param_name="New Status",
            input_type=str,
            is_mandatory=True,
            print_value=True,
        )

        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        violation_id = validate_required_string(violation_id, "Violation ID")
        violation_id = validate_uuid_format(violation_id, "Violation ID")
        new_status_api = validate_new_status(new_status_label)

        manager = APIManager(
            service_account_json,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        # bulkUpdatePolicyViolations is shared across DSPM and IR violation types —
        # RSC's mutation only cares about policyViolationIds + newPolicyViolationStatus,
        # so this single action works for a violation ID from either source.
        manager.update_violation_status(
            violation_ids=[violation_id],
            new_status=new_status_api,
        )

        output_message = (
            f"Violation status updated to '{new_status_label}' "
            f"for violation ID: {violation_id}."
        )
        siemplify.LOGGER.info(output_message)

    except (InvalidValueException, ValueError) as e:
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
            "Failed to update violation status", e
        )
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except RubrikException as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            UPDATE_VIOLATION_STATUS_SCRIPT_NAME, e
        )
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            UPDATE_VIOLATION_STATUS_SCRIPT_NAME, e
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


def validate_new_status(new_status_label) -> str:
    """Validate & map the New Status parameter per the Update Violation Status spec.

    Raises:
        InvalidValueException: With the exact wording required by the action's
            case wall output message contract.
    """
    valid_labels = list(STATUS_ENUM_MAP.keys())

    if not new_status_label or not new_status_label.strip():
        raise InvalidValueException(f"New Status is required. Valid values: {valid_labels}")

    new_status_label = new_status_label.strip()
    if new_status_label not in STATUS_ENUM_MAP:
        raise InvalidValueException(
            f"Invalid value '{new_status_label}' for parameter 'New Status'. "
            f"Valid values: {valid_labels}"
        )

    return STATUS_ENUM_MAP[new_status_label]


if __name__ == "__main__":
    main()
