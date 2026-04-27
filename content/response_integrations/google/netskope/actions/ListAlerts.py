from __future__ import annotations
import json
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import (
    extract_action_param,
    construct_csv,
    dict_to_flat,
)
from ..core import exceptions
from ..core.NetskopeManagerFactory import NetskopeManagerFactory

INTEGRATION_NAME = "Netskope"
LISTALERTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - ListAlerts"
CSV_TABLE_NAME = "Netskope - Alerts"
DEFAULT_LIMIT = 100


def validate_alert_type(alert_type: str) -> None:
    """
    Validate Alert Type.

    :param alert_type: (str) The alert type.
    """
    if alert_type not in [
        "anomaly",
        "Compromised Credential",
        "policy",
        "Legal Hold",
        "malsite",
        "Malware",
        "DLP",
        "watchlist",
        "quarantine",
        "Remediation",
    ]:
        raise exceptions.NetskopeParamError("Invalid Alert Type")


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LISTALERTS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Parameters
    query = extract_action_param(
        siemplify, param_name="Query", is_mandatory=False, print_value=True
    )
    alert_type = extract_action_param(
        siemplify, param_name="Type", is_mandatory=False, print_value=True
    )
    time_period = extract_action_param(
        siemplify, param_name="Time Period", is_mandatory=False, print_value=True
    )
    start_time = extract_action_param(
        siemplify, param_name="Start Time", is_mandatory=False, print_value=True
    )
    end_time = extract_action_param(
        siemplify, param_name="End Time", is_mandatory=False, print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Limit",
        is_mandatory=False,
        default_value=DEFAULT_LIMIT,
        input_type=int,
        print_value=True,
    )
    acked = extract_action_param(
        siemplify,
        param_name="Is Acknowledged",
        is_mandatory=False,
        default_value=False,
        input_type=bool,
        print_value=True,
    )

    if limit <= 0:
        siemplify.LOGGER.info(
            f"The limit is less than zero, using default limit {DEFAULT_LIMIT} instead."
        )
        limit = DEFAULT_LIMIT

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    siemplify.LOGGER.info("Starting to perform the action")
    status = EXECUTION_STATE_FAILED
    json_results = []
    output_alerts = ""

    try:
        if alert_type:
            validate_alert_type(alert_type=alert_type)
        netskope_manager = NetskopeManagerFactory.get_manager(
            siemplify, api_version="v2"
        )
        alerts_gen = netskope_manager.get_alerts(
            query=query,
            alert_type=alert_type,
            timeperiod=time_period,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            acked=acked,
        )
        alerts = list(alerts_gen)
        siemplify.logger.info(f"alerts: {alerts}")

        if alerts:
            output_message = f"Found {len(alerts)} alerts"
            json_results = alerts
            flat_alerts = list(map(dict_to_flat, alerts))
            csv_output = construct_csv(flat_alerts)
            siemplify.result.add_data_table(CSV_TABLE_NAME, csv_output)
            # add json
            siemplify.result.add_result_json(json.dumps(json_results))
            output_alerts = json.dumps(alerts)

        else:
            output_message = "Found 0 alerts, error: no alerts found"
            if isinstance(alerts, str):
                raise exceptions.NetskopeDataNotFoundError(alerts)
        siemplify.LOGGER.info("Finished performing the action")
        status = EXECUTION_STATE_COMPLETED

    except exceptions.NetskopeParamError as e:
        output_message = f"Failed to connect to the {INTEGRATION_NAME}! Error: {e}"
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = f'Error executing action "ListAlerts". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, output_alerts, status)


if __name__ == "__main__":
    main()
