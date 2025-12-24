from __future__ import annotations

import copy
import sys
import time

import duo_client
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import CaseInfo
from soar_sdk.SiemplifyUtils import output_handler

INTEGRATION_NAME = "DUO"
CONNECTOR_NAME = "DUO-Trust Monitor Connector"
NAME = "DUO Trust Monitor"
VENDOR = "CISCO"
PRODUCT = "DUO MFA"
RULE_GENERATOR = "DUO Trust Monitor"
NO_RESULTS = "No Trust Monitor Events found"
RANDOM_ALERT_COUNT_MAX = 3
RANDOM_EVENT_COUNT_PER_ALERT_MAX = 5


def get_unicode(test):
    return str(test)


def dict_to_flat(target_dict):
    """Receives nested dictionary and returns it as a flat dictionary.
    :param target_dict: {dict}
    :return: Flat dict : {dict}
    """
    target_dict = copy.deepcopy(target_dict)

    def expand(raw_key, raw_value):
        key = raw_key
        value = raw_value
        """
        :param key: {string}
        :param value: {string}
        :return: Recursive function.
        """
        if value is None:
            return [(get_unicode(key), "")]
        if isinstance(value, dict):
            # Handle dict type value
            return [
                (
                    f"{get_unicode(key)}_{get_unicode(sub_key)}",
                    get_unicode(sub_value),
                )
                for sub_key, sub_value in dict_to_flat(value).items()
            ]
        if isinstance(value, list):
            # Handle list type value
            count = 1
            l = []
            items_to_remove = []
            for value_item in value:
                if isinstance(value_item, dict):
                    # Handle nested dict in list
                    l.extend(
                        [
                            (
                                f"{get_unicode(key)}_{get_unicode(count)}_{get_unicode(sub_key)}",
                                sub_value,
                            )
                            for sub_key, sub_value in dict_to_flat(value_item).items()
                        ],
                    )
                    items_to_remove.append(value_item)
                    count += 1
                elif isinstance(value_item, list):
                    l.extend(
                        expand(get_unicode(key) + "_" + get_unicode(count), value_item),
                    )
                    count += 1
                    items_to_remove.append(value_item)
            for value_item in items_to_remove:
                value.remove(value_item)
            for value_item in value:
                l.extend([(get_unicode(key) + "_" + get_unicode(count), value_item)])
                count += 1
            return l
        return [(get_unicode(key), get_unicode(value))]

    items = [
        item
        for sub_key, sub_value in target_dict.items()
        for item in expand(sub_key, sub_value)
    ]
    return dict(items)


def create_event(siemplify, alert_id, trust_mon_event_data):
    """Returns the digested data of a single unread email"""
    siemplify.LOGGER.info(
        f"--- Started processing Event: alert_id: {alert_id} | event_id: {alert_id}",
    )

    event = {}
    # event = trust_mon_event_data
    event["message_id"] = alert_id
    event["name"] = NAME
    event["time"] = trust_mon_event_data["surfaced_auth"]["timestamp"] * 1000
    event["StartTime"] = trust_mon_event_data["surfaced_auth"]["timestamp"] * 1000
    event["EndTime"] = trust_mon_event_data["surfaced_auth"]["timestamp"] * 1000
    event["event_name"] = "DUO Trust Monitor Event"
    event["device_product"] = PRODUCT
    event["device_vendor"] = VENDOR
    event["Subject"] = (
        trust_mon_event_data["type"]
        + " event for "
        + trust_mon_event_data["surfaced_auth"]["user"]["name"]
    )
    event["SourceUserName"] = trust_mon_event_data["surfaced_auth"]["user"]["name"]
    event["events"] = [dict_to_flat(trust_mon_event_data)]

    siemplify.LOGGER.info(
        f"--- Finished processing Event: alert_id: {alert_id} | event_id: {alert_id}",
    )

    return event


def create_alert(siemplify, alert_id, trust_mon_event_data):
    """Returns an alert which is one event that contains one Trust Monitor Connector event"""
    siemplify.LOGGER.info(f"-------------- Started processing Alert {alert_id}")

    created_event = create_event(siemplify, alert_id, trust_mon_event_data)

    case_info = CaseInfo()
    case_info.name = (
        trust_mon_event_data["type"]
        + " event for "
        + trust_mon_event_data["surfaced_auth"]["user"]["name"]
    )
    case_info.rule_generator = RULE_GENERATOR
    case_info.start_time = trust_mon_event_data["surfaced_auth"]["timestamp"] * 1000
    case_info.end_time = trust_mon_event_data["surfaced_auth"]["timestamp"] * 1000
    case_info.identifier = alert_id
    case_info.ticket_id = alert_id
    case_info.display_id = alert_id
    case_info.priority = (
        60  # Informative = -1,Low = 40,Medium = 60,High = 80,Critical = 100.
    )
    case_info.device_vendor = VENDOR
    case_info.device_product = PRODUCT
    # case_info.events = [trust_mon_event_data]
    # case_info.events = [dict_to_flat(trust_mon_event_data)]
    case_info.events = [dict_to_flat(created_event)]
    # case_info.events.append([dict_to_flat(created_event)])

    siemplify.LOGGER.info(f"-------------- Events creating started for {alert_id}")

    return case_info


def get_duo_trust_mon_data(duoApi, adminSec, adminIntKey, days_back):
    """Returns trusted monitor events in past x days"""
    days_back = int(days_back)
    x_days_back = (86400 * 1000) * days_back
    timestamp_now = int(time.time() * 1000)
    timestamp_x_days_ago = timestamp_now - x_days_back

    trust_monitor = "None"
    try:
        # parameters
        x_days_back = (86400 * 1000) * days_back
        timestamp_now = int(time.time() * 1000)
        timestamp_x_days_ago = timestamp_now - x_days_back

        admin_api = duo_client.Admin(ikey=adminIntKey, skey=adminSec, host=duoApi)
        trust_monitor = admin_api.get_trust_monitor_events_by_offset(
            maxtime=timestamp_now,
            mintime=timestamp_x_days_ago,
        )
        # json_result = json.dumps(tru)
        # output_message = "Results: {}".format(json_result)

    except Exception as e:
        raise Exception(e)

    return trust_monitor


@output_handler
def main(is_test_run=False):
    alerts = []  # The main output of each connector run
    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper
    siemplify.script_name = CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******',
        )
    else:
        siemplify.LOGGER.info(
            "==================== Begin DUO Connector ====================",
        )
    duoApi = siemplify.extract_connector_param(param_name="API Hostname")
    adminIntKey = siemplify.extract_connector_param(param_name="Admin Integration Key")
    adminSec = siemplify.extract_connector_param(param_name="Admin Secret Key")
    days_back = siemplify.extract_connector_param(param_name="Days Back")

    siemplify.LOGGER.info("------------------- Main - Started -------------------")

    duo_trust_mon_data = get_duo_trust_mon_data(
        duoApi,
        adminSec,
        adminIntKey,
        days_back,
    )

    # print(duo_trust_mon_data['events'])
    for data in duo_trust_mon_data["events"]:
        alert_id = data["surfaced_auth"]["txid"]

        created_alert = create_alert(siemplify, alert_id, data)
        alerts.append(created_alert)
        siemplify.LOGGER.info(f"Added Alert {alert_id} to package results")

    # Return created alerts
    siemplify.return_package(alerts)


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
