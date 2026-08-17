from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    GET_IR_VIOLATION_DETAILS_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import IRViolationDetails
from ..core.rubrik_exceptions import (
    GraphQLQueryException,
    InvalidValueException,
    ItemNotFoundException,
    RubrikException,
    UnauthorizedErrorException,
)
from ..core.utils import (
    format_authentication_failure_message,
    format_graphql_error_message,
    get_integration_params,
    parse_ir_policy_types_param,
    validate_required_string,
    validate_uuid_format,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_IR_VIOLATION_DETAILS_SCRIPT_NAME
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
        policy_types = parse_ir_policy_types_param(siemplify)

        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        violation_id = validate_uuid_format(
            validate_required_string(violation_id, "Violation ID"), "Violation ID"
        )

        manager = APIManager(
            service_account_json,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        data = manager.get_ir_violation_details(violation_id, policy_types)
        json_results = [data]
        violation_raw = data.get("policyViolation", {})
        details_model = IRViolationDetails(violation_raw)
        table_data = [details_model.to_csv()]
        siemplify.result.add_data_table("IR Violation Details", construct_csv(table_data))

        if details_model.manual_remediation:
            siemplify.add_comment(
                f"RSC IR Remediation Guidance:\n{details_model.manual_remediation}"
            )
            siemplify.LOGGER.info("Added manual remediation process as case comment.")

        output_message = (
            f"Successfully retrieved IR violation details for ID: {violation_id}. "
            f"Identity: {details_model.display_name or 'N/A'} "
            f"({details_model.user_principal_name or 'N/A'})."
        )
        siemplify.LOGGER.info(output_message)
        siemplify.LOGGER.info(
            f"userPrincipalName={details_model.user_principal_name} — "
            "use as notification target in IR playbook."
        )

    except (InvalidValueException, ItemNotFoundException, ValueError) as e:
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
        output_message = format_graphql_error_message("API error during Get IR Violation Details", e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except RubrikException as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            GET_IR_VIOLATION_DETAILS_SCRIPT_NAME, e
        )
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            GET_IR_VIOLATION_DETAILS_SCRIPT_NAME, e
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
