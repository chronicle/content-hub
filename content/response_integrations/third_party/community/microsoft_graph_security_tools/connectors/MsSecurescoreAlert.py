from __future__ import annotations

import json
import sys
import uuid

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now

from ..core.MicrosoftGraphSecurityManager import MicrosoftGraphSecurityManager

CONNECTOR_NAME = "MS SecureScore Alert"
VENDOR = "Microsoft"
PRODUCT = "Microsoft 365"
RULE_GENERATOR = "SecureScore"
RANDOM_ALERT_COUNT_MAX = 3
RANDOM_EVENT_COUNT_PER_ALERT_MAX = 5


@output_handler
def main(is_test_run):
    alerts = []  # The main output of each connector run
    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper
    siemplify.script_name = CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******',
        )

    siemplify.LOGGER.info("==================== Main - Param Init ====================")

    client_id = siemplify.extract_connector_param(
        param_name="Client ID",
        print_value=True,
    )
    secret_id = siemplify.extract_connector_param(
        param_name="Secret ID",
        print_value=False,
    )
    tenant = siemplify.extract_connector_param(
        param_name="Tenant ID",
        print_value=False,
    )
    certificate_password = siemplify.extract_connector_param(
        param_name="Certificate Password",
        print_value=False,
    )
    certificate_path = siemplify.extract_connector_param(
        param_name="Certificate Path",
        print_value=True,
    )
    threshold = siemplify.extract_connector_param(
        param_name="Threshold",
        print_value=False,
    )
    priority = siemplify.extract_connector_param(
        param_name="Default Priority",
        print_value=False,
    )

    siemplify.LOGGER.info("------------------- Main - Started -------------------")

    json_results = {}

    try:
        siemplify.LOGGER.info("Connecting to Microsoft Graph Security.")
        mtm = MicrosoftGraphSecurityManager(
            client_id,
            secret_id,
            certificate_path,
            certificate_password,
            tenant,
        )
        siemplify.LOGGER.info("Connected successfully.")

        secure_score = mtm.get_secure_score()

        if secure_score:
            siemplify.LOGGER.info("Retrieved SecureScore.")

            if int(secure_score[0]["currentScore"]) < int(threshold):
                try:
                    alert_id = secure_score[0]["id"]
                    alert = fetch_alert(siemplify, alert_id, secure_score[0])

                    if alert:
                        alerts.append(alert)
                        siemplify.LOGGER.info(
                            f"Added Alert {alert_id} to package results",
                        )

                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Failed to process alert {alert_id}",
                        alert_id=alert_id,
                    )
                    siemplify.LOGGER.exception(e)

                json_results = json.dumps(secure_score)
                output_message = "SecureScore information was found."
                result_value = json.dumps(secure_score)
            else:
                siemplify.LOGGER.info(
                    f"Currect score {secure_score[0]['currentScore']!s} is greater than threshold {threshold!s}. No alerts created. ",
                )

        else:
            siemplify.LOGGER.info("No SecureScore information was found.")
            output_message = "No SecureScore information was found."
            result_value = json.dumps({})

    except Exception as e:
        siemplify.LOGGER.error(f"Some errors occurred. Error: {e}")
        siemplify.LOGGER.exception(e)
        result_value = json.dumps({})
        output_message = f"Some errors occurred. Error: {e}"
        raise

    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(alerts)


def fetch_alert(siemplify, alert_id, secure_score):
    siemplify.LOGGER.info(
        f"-------------- Started processing Alert {alert_id}",
        alert_id=alert_id,
    )

    alert_info = AlertInfo()
    alert_info.display_id = str(uuid.uuid4())
    alert_info.ticket_id = alert_id
    alert_info.name = "MS SecureScore Below Thresold"
    alert_info.rule_generator = RULE_GENERATOR
    alert_info.start_time = unix_now()
    alert_info.end_time = unix_now()
    alert_info.priority = (
        priority  # Informative = -1,Low = 40,Medium = 60,High = 80,Critical = 100.
    )
    alert_info.device_vendor = VENDOR
    alert_info.device_product = PRODUCT
    # ----------------------------- Alert Fields initilization END -----------------------------

    siemplify.LOGGER.info(f"---------- Events fetching started for alert  {alert_id}")

    event_id = str(uuid.uuid4())
    try:
        event = fetch_event(siemplify, alert_id, event_id, secure_score)

        if event:
            alert_info.events.append(event)
            siemplify.LOGGER.info(f"Added Event {event_id} to Alert {alert_id}")
        else:
            siemplify.LOGGER.info("Event failed to process, moving on")

    except Exception as e:
        siemplify.LOGGER.error(f"Failed to process event {event_id}", alert_id=alert_id)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info(f"---------- Events fetching finished for alert {alert_id}")

    siemplify.LOGGER.info(
        f"-------------- Finished processing Alert {alert_id}",
        alert_id=alert_id,
    )
    return alert_info


def fetch_event(siemplify, alert_id, event_id, secure_score):
    siemplify.LOGGER.info(
        f"--- Started processing Event:  alert_id: {alert_id} | event_id: {event_id}",
    )
    event = {}

    # ----------- Mandatory Fields ----------------
    event["StartTime"] = unix_now()
    event["EndTime"] = unix_now()
    event["name"] = "MFA problem detection"
    event["device_product"] = "Microsoft 365"
    # ----------------------------- ---------------

    # General fields
    event["activeUserCount"] = secure_score["activeUserCount"]
    event["createdDateTime"] = secure_score["createdDateTime"]
    event["currentScore"] = secure_score["currentScore"]
    event["enabledServices"] = str(secure_score["enabledServices"])
    event["AllTenantAverage"] = secure_score["averageComparativeScores"][0][
        "averageScore"
    ]
    event["TotalSeatsAverage"] = secure_score["averageComparativeScores"][1][
        "averageScore"
    ]
    event["IndustryAverage"] = secure_score["averageComparativeScores"][2][
        "averageScore"
    ]
    event["controlScores"] = str(secure_score["controlScores"])

    siemplify.LOGGER.info(
        f"--- Finished processing Event: alert_id: {alert_id} | event_id: {event_id}",
    )

    return event


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
