from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import construct_csv, extract_action_param, extract_configuration_param

from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    INTEGRATION_NAME,
    RESOLVE_ASSIGNMENT_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.UtilsManager import validate_integer, validate_triage
from ..core.VectraQUXExceptions import InvalidIntegerException, VectraQUXException
from ..core.VectraQUXManager import VectraQUXManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = RESOLVE_ASSIGNMENT_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        input_type=str,
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        input_type=str,
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    # Action Parameters
    assignment_id = extract_action_param(
        siemplify,
        param_name="Assignment ID",
        input_type=str,
        is_mandatory=True,
    )
    outcome_id = extract_action_param(
        siemplify,
        param_name="Outcome ID",
        input_type=str,
        is_mandatory=True,
    )
    note_title = extract_action_param(
        siemplify,
        param_name="Note Title",
        input_type=str,
        is_mandatory=False,
        default_value="",
    )
    triage_as = extract_action_param(
        siemplify,
        param_name="Triage As",
        input_type=str,
        is_mandatory=False,
        default_value="",
    )
    detection_ids = extract_action_param(
        siemplify,
        param_name="Detection IDs",
        input_type=str,
        is_mandatory=False,
        default_value="",
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE

    try:
        assignment_id = validate_integer(assignment_id, field_name="Assignment ID")
        outcome_id = validate_integer(outcome_id, field_name="Outcome ID")
        if detection_ids != "":
            detection_ids = [
                validate_integer(detection_id.strip(), field_name="Detection IDs")
                for detection_id in detection_ids.split(",")
                if detection_id.strip()
            ]

        if triage_as != "":
            validate_triage(triage_as)

        if triage_as != "" and detection_ids == "":
            raise VectraQUXException(
                "At least one detection ID is required while using triage as.",
            )

        vectra_manager = VectraQUXManager(
            api_root,
            api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        response, assignment = vectra_manager.resolve_assignment(
            assignment_id,
            outcome_id,
            note_title,
            triage_as,
            detection_ids,
        )

        output_message = f"Successfully resolved assignment ID {assignment_id}"

        siemplify.result.add_result_json(json.dumps(response, indent=4))
        # add response to csv
        siemplify.result.add_data_table(
            title="Resolved Assignment",
            data_table=construct_csv([assignment.list_assignment_csv()]),
        )

    except InvalidIntegerException as e:
        status = EXECUTION_STATE_FAILED
        output_message = f"{e}"
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except VectraQUXException as e:
        status = EXECUTION_STATE_FAILED
        if str(e) == "Not found.":
            output_message = "Assignment ID not found."
        else:
            output_message = str(e).strip("[]").strip("''")
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(INTEGRATION_NAME, e)
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"is_success: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
