from __future__ import annotations

import json
import re
import sys
import traceback

from sixgill.sixgill_constants import FeedStream
from sixgill.sixgill_feed_client import SixgillFeedClient
from sixgill.sixgill_utils import is_indicator
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now

# ==============================================================================
# This is a Connector Template + mock generator. This file objective is to demonstrate how to build a connector, and exmplain the objective of each field.
# All the data generated here, is MOCK data. Enjoy.
# ==============================================================================

CONNECTOR_NAME = "CyberSixgill Darkfeed"
VENDOR = "Cybersixgill"
PRODUCT = "Cybersixgill Darkfeed"
RULE_GENERATOR_EXAMPLE = "CyberSixgill Darkfeed"
SIXGILL_CHANNEL_ID = "1f4fdd520d3a721799fc0d044283d364"


@output_handler
def main(is_test_run):
    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper
    siemplify.script_name = CONNECTOR_NAME
    alerts = []  # The main output of each connector run

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******',
        )

    siemplify.LOGGER.info("==================== Main - Param Init ====================")
    client_id = siemplify.extract_connector_param(
        "Client Id",
        default_value=None,
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )
    client_secret = siemplify.extract_connector_param(
        "Client Secret",
        default_value=None,
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )
    bulk_size = siemplify.extract_connector_param(
        "Alerts Limit",
        default_value=None,
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )
    siemplify.LOGGER.info("------------------- Main - Started -------------------")
    sixgill_client = create_sixgill_client_obj(
        siemplify,
        client_id,
        client_secret,
        SIXGILL_CHANNEL_ID,
        bulk_size,
    )
    records = query_sixgill(sixgill_client)
    siemplify.LOGGER.info("True")
    if records:
        for rec in records:
            try:
                if not rec.get("revoked", False):
                    alert_data = fetch_alert(siemplify, rec)
                if alert_data:
                    siemplify.LOGGER.info("\n\n\n")
                    siemplify.LOGGER.info(alert_data)
                    siemplify.LOGGER.info("\n\n\n")
                    alerts.append(alert_data)
            except Exception as e:
                siemplify.LOGGER.exception(e)
    sixgill_client.commit_indicators()
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(alerts)


def fetch_alert(siemplify, record_data):
    """Returns an alert, which is an aggregation of basic events. (ie: Arcsight's correlation, QRadar's Offense)"""
    alert_info = AlertInfo()
    # ----------------------------- Alert Fields initilization START -----------------------------
    # ... Replace this DUMMY VALUES !!! ...
    # Each alert_info has a unique key composed of alert_info.name+alert_info.display_id. This key is used to validate data is digested only once by the Siemplify System - to avoid duplicates.
    # If an alert_info has a uniqe_key that has already been digested, it will be ignored.
    # The uniqueness must be persistent, even after server restart\ refetching of the same alert, multiple runs of the same API queries, etc.
    alert_info.display_id = record_data.get("id")[11:]
    alert_info.ticket_id = record_data.get(
        "id",
    )[
        11:
    ]  # In default, ticket_id = display_id. But, if for some reason the external alert id, is different then the composite's key display_id, you can save the original external alert id in this "ticket_id" field.
    alert_info.name = record_data.get("description")
    alert_info.rule_generator = RULE_GENERATOR_EXAMPLE  # Describes the name of the siem's rule, that caused the aggregation of the alert.
    alert_info.start_time = unix_now()  # Times should be saved in UnixTime. You may use SiemplifyUtils.convert_datetime_to_unix_time, or SiemplifyUtils.convert_string_to_datetime
    alert_info.end_time = unix_now()  # Times should be saved in UnixTime. You may use SiemplifyUtils.convert_datetime_to_unix_time, or SiemplifyUtils.convert_string_to_datetime
    alert_info.priority = (
        60  # Informative = -1,Low = 40,Medium = 60,High = 80,Critical = 100.
    )
    alert_info.device_vendor = VENDOR  # This field, may be fetched from the Original Alert. If you build this alert manualy, Describe the source vendor of the data. (ie: Microsoft, Mcafee)
    alert_info.device_product = PRODUCT  # This field, may be fetched from the Original Alert. If you build this alert manualy, Describe the source product of the data. (ie: ActiveDirectory, AntiVirus)
    event_info = fetch_event(siemplify, record_data)
    alert_info.events.append(event_info)
    return alert_info


def query_sixgill(sixgill_client):
    records_object = None
    try:
        raw_response = sixgill_client.get_bundle()
        records_object = list(filter(is_indicator, raw_response.get("objects", [])))
    except Exception as err:
        siemplify.LOGGER.error(err)
        siemplify.LOGGER.error(traceback.format_exc())
    return records_object


def get_external_reference(event, record_data):
    try:
        for obj in record_data.get("external_reference", []):
            if obj.get("source_name", "") == "VirusTotal":
                event["SixgillVirustotalPR"] = obj.get("positive_rate")
                event["SixgillVirustotalUrl"] = obj.get("url")
            if obj.get("source_name", "") == "mitre-attack":
                event["SixgillMitreDescription"] = obj.get("description")
                event["SixgillMitreTactic"] = obj.get("mitre_attack_tactic")
                event["SixgillMitreTacticId"] = obj.get("mitre_attack_tactic_id")
                event["SixgillMitreTacticUrl"] = obj.get("mitre_attack_tactic_url")
    except Exception as err:
        siemplify.LOGGER.error(err)
    return event


def fetch_event(siemplify, record_data):
    REGEX_PARSER = re.compile(
        r"([\w-]+?):(\w.+?) (?:[!><]?=|IN|MATCHES|LIKE) '(.*?)' *[OR|AND|FOLLOWEDBY]?",
    )
    event = {}
    # ----------- Mandatory Fields ---------------
    # A valid event must have a "Start Time", "End Time", "Name", and "Device Product". Their name is not important (What ever it is, it will be mapped).
    # ie: "Start Time" may be called "Start Time", "StartTime", "start_time", "johnDoeStartTime"
    event["StartTime"] = (
        unix_now()
    )  # Times should be saved in UnixTime. You may use SiemplifyUtils.convert_datetime_to_unix_time, or SiemplifyUtils.convert_string_to_datetime
    event["EndTime"] = (
        unix_now()
    )  # Times should be saved in UnixTime. You may use SiemplifyUtils.convert_datetime_to_unix_time, or SiemplifyUtils.convert_string_to_datetime
    event["name"] = record_data.get("description")
    event["device_product"] = (
        PRODUCT  # ie: "device_product" is the field name in arcsight that describes the product the event originated from.
    )
    # ----------------------------- ---------------
    # You are not expected to fill them yourself, just pass them along from the siem. Since this is a dummy generator, We create them manaualy with made up name (PascalCase\CcmelCase doesn't matter)
    for indicator_type, sub_type, value in REGEX_PARSER.findall(
        record_data.get("pattern", ""),
    ):
        if indicator_type == "file":
            if "MD5" in sub_type:
                event["Sixgill_MD5_IOC"] = value
            elif "SHA-1" in sub_type:
                event["Sixgill_SHA-1_IOC"] = value
            elif "SHA-256" in sub_type:
                event["Sixgill_SHA-256_IOC"] = value
        elif indicator_type == "url":
            event["Sixgill_URL_IOC"] = value
        elif indicator_type == "domain-name":
            event["Sixgill_Domain_IOC"] = value
        elif indicator_type == "ipv4-addr":
            event["Sixgill_IP_IOC"] = value
    event["Sixgill_RawJson"] = json.dumps(record_data)
    event["SixgillDescription"] = record_data.get("description")
    event["SixgillFeedname"] = record_data.get("sixgill_feedname")
    event["SixgillSource"] = record_data.get("sixgill_source")
    event["SixgillPostTitle"] = record_data.get("sixgill_posttitle")
    event["SixgillActor"] = record_data.get("sixgill_actor")
    event["SixgillPostID"] = (
        "https://portal.cybersixgill.com/#/search?q=_id:"
        + record_data.get("sixgill_postid", "")
    )
    event["SixgillLabels"] = ",".join(record_data.get("labels"))
    event["SixgillConfidence"] = record_data.get("sixgill_confidence")
    event["SixgillSeverity"] = record_data.get("sixgill_severity")
    event["SixgillCreated"] = record_data.get("created")
    event["SixgillModified"] = record_data.get("modified")
    event["SixgillValidFrom"] = record_data.get("valid_from")

    event = get_external_reference(event, record_data)

    return event


def create_sixgill_client_obj(
    siemplify,
    client_id,
    client_secret,
    channel_id,
    bulk_size,
):
    """This create a sixgill client object

    Returns:
        sixgill.sixgill_feed_client.SixgillFeedClient -- Sixgill Client object

    """
    sixgill_darkfeed_client = None
    try:
        sixgill_darkfeed_client = SixgillFeedClient(
            client_id,
            client_secret,
            channel_id,
            FeedStream.DARKFEED,
            bulk_size=bulk_size,
            verify=True,
        )
    except Exception as err:
        siemplify.LOGGER.error("create_sixgill_client_obj - Error - " + str(err))
        siemplify.LOGGER.info(traceback.format_exc())
    return sixgill_darkfeed_client


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
