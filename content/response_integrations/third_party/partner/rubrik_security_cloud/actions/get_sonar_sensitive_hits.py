from __future__ import annotations

import json
from datetime import datetime, timedelta

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    DEFAULT_SEARCH_TIME_PERIOD,
    DEFAULT_TIMEZONE,
    GET_SONAR_SENSITIVE_HITS_SCRIPT_NAME,
    MAX_TABLE_RECORDS,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import SonarSensitiveHitsDatamodel
from ..core.rubrik_exceptions import RubrikException
from ..core.utils import (
    get_integration_params,
    validate_integer_param,
    validate_required_string,
)


@output_handler
def main():
    """Retrieve Sonar Sensitive Hits for a specified object from Rubrik Security Cloud.

    This action retrieves sensitive data hits detected by Rubrik Sonar for a specific object
    within a configurable lookback period. Sonar is Rubrik's data classification and
    sensitive data discovery engine.

    Action Parameters:
        Object Name (str, required): Name of the object to retrieve sensitive hits for
        Lookback Days (str, optional): Number of days to look back for sensitive hits (default: 7)

    Returns:
        None. Results are returned via siemplify.end() with:
            - output_message (str): Status message describing the retrieval results
            - result_value (str): "true" if successful, "false" otherwise
            - status (str): Execution state (COMPLETED or FAILED)

    Raises:
        ValueError: If parameter validation fails (e.g., invalid object name or lookback days)
        RubrikException: If API calls to Rubrik Security Cloud fail
        Exception: For any other unexpected errors during execution
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_SONAR_SENSITIVE_HITS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    service_account_json, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    object_name = siemplify.extract_action_param(
        param_name="Object Name", input_type=str, is_mandatory=True
    )
    search_time_period = siemplify.extract_action_param(
        param_name="Lookback Days",
        input_type=str,
        is_mandatory=False,
        default_value=DEFAULT_SEARCH_TIME_PERIOD,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = RESULT_VALUE_TRUE

    try:
        object_name = validate_required_string(object_name, "Object Name")

        search_time_period = validate_integer_param(
            search_time_period,
            "Lookback Days",
            zero_allowed=True,
            allow_negative=False,
            default_value=DEFAULT_SEARCH_TIME_PERIOD,
        )

        # Calculate the date for the search time period
        search_date = (datetime.now() - timedelta(days=search_time_period)).strftime("%Y-%m-%d")

        siemplify.LOGGER.info("Initializing Rubrik Security Cloud client")
        rubrik_manager = APIManager(
            service_account_json,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        siemplify.LOGGER.info(f"Retrieving Sonar Sensitive Hits for Object: {object_name}")
        siemplify.LOGGER.info(f"Search date used for fetching Sonar sensitive hits: {search_date}")

        # Get object details (internally handles both GraphQL queries)
        object_detail_response = rubrik_manager.get_sonar_object_detail(
            object_name=object_name,
            day=search_date,
            timezone=DEFAULT_TIMEZONE,
        )

        siemplify.result.add_result_json(json.dumps(object_detail_response))

        data = object_detail_response.get("data", {})
        policy_obj = data.get("policyObj", {})

        sensitive_hits_data = SonarSensitiveHitsDatamodel(policy_obj)

        output_message = (
            f"Successfully retrieved Sonar Sensitive Hits for Object: {object_name}"
            f"Showing up to {MAX_TABLE_RECORDS} records in table."
        )
        table_data = sensitive_hits_data.to_csv()
        consise_table_data = table_data[:MAX_TABLE_RECORDS]
        if consise_table_data:
            siemplify.result.add_data_table(
                "Sonar Sensitive Hits", construct_csv(consise_table_data), "RSC"
            )

    except (RubrikException, ValueError) as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            GET_SONAR_SENSITIVE_HITS_SCRIPT_NAME, str(e)
        )
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
