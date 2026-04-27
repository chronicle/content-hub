from __future__ import annotations
from ..core.ArmisManager import ArmisManager
from ..core.consts import (
    INTEGRATION_NAME,
    DEFAULT_SEVERITY,
    DEFAULT_CONNECTIONS_TO_FETCH,
    SEVERITIES_FILTER_MAPPING,
    ALERT_CONNECTIONS_TABLE,
    LIST_ALERT_CONNECTIONS,
    MIN_CONNECTIONS_TO_RETURN,
)

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.exceptions import ArmisValidationException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {LIST_ALERT_CONNECTIONS}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # Integration configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Secret",
        is_mandatory=True,
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=True,
        is_mandatory=False,
        print_value=True,
    )

    severity = extract_action_param(
        siemplify,
        param_name="Lowest Severity To Fetch",
        is_mandatory=False,
        print_value=True,
        default_value=DEFAULT_SEVERITY,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    json_result = []
    csv_list = []
    result_value = False

    try:
        alert_id = extract_action_param(
            siemplify,
            param_name="Alert ID",
            is_mandatory=True,
            input_type=int,
            print_value=True,
        )

        max_connections_to_fetch = extract_action_param(
            siemplify,
            param_name="Max Connections To Return",
            is_mandatory=False,
            input_type=int,
            print_value=True,
            default_value=DEFAULT_CONNECTIONS_TO_FETCH,
        )

        if max_connections_to_fetch < MIN_CONNECTIONS_TO_RETURN:
            raise ArmisValidationException(
                "'Max Connections To Return' parameter must be greater"
                f" or equal to {MIN_CONNECTIONS_TO_RETURN}"
            )

        manager = ArmisManager(
            api_root=api_root, api_secret=api_secret, verify_ssl=verify_ssl
        )

        siemplify.LOGGER.info(
            f"Fetching alert connections from {INTEGRATION_NAME} service"
        )
        query = (
            "in:connections riskLevel:"
            f"{SEVERITIES_FILTER_MAPPING.get(severity.upper(), None)}"
            f" activity:(alert:(alertId:({alert_id})))"
        )
        alert_connections = manager.get_alert_connections(
            aql=query, max_alert_connections_to_fetch=max_connections_to_fetch
        )
        siemplify.LOGGER.info(
            f"Successfully fetched {len(alert_connections)}"
            f" alert connections from {INTEGRATION_NAME} service"
        )

        if alert_connections:
            siemplify.LOGGER.info(
                f"Processing alert connections of alert with ID: {alert_id}"
            )
            for connection in alert_connections:
                json_result.append(connection.as_json())
                csv_list.append(connection.as_csv())

            siemplify.result.add_result_json(json_result)
            siemplify.result.add_data_table(
                ALERT_CONNECTIONS_TABLE, construct_csv(csv_list)
            )
            siemplify.LOGGER.info(
                "Successfully processed alert connections of alert with ID: "
                f"{alert_id}"
            )

            result_value = True
            output_message = (
                "Successfully returned connections related to the alert"
                f" {alert_id} based on the "
                f"provided criteria in {INTEGRATION_NAME}."
            )

        else:
            output_message = (
                f"No connections were found related to the alert {alert_id} "
                f"based on the provided criteria in {INTEGRATION_NAME}."
            )

        status = EXECUTION_STATE_COMPLETED

    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action '{LIST_ALERT_CONNECTIONS}'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
