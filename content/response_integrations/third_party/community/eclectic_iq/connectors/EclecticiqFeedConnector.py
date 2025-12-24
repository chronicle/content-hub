from __future__ import annotations

import json
import sys
import uuid

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon import read_ids, write_ids

from ..core.EclecticIQManager import EclecticIQManager

CONNECTOR_NAME = "Feed Connector"
VENDOR = "EclecticIQ"
PRODUCT = "EclecticIQ Intelligence Center"
RULE_GENERATOR_EXAMPLE = "EclecticIQ Outgoing Feed"
INTEGRATION_NAME = "EclecticIQ"


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

    eiq_url = siemplify.extract_connector_param(
        "EclecticIQ URL",
        default_value=None,
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )
    api_token = siemplify.extract_connector_param(
        "API Token",
        default_value=None,
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )
    verify_ssl = siemplify.extract_connector_param(
        "Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    outgoing_feed_id = siemplify.extract_connector_param("Outgoing Feed ID")

    siemplify.LOGGER.info("------------------- Main - Started -------------------")

    eiq_manager = EclecticIQManager(eiq_url, api_token, verify_ssl)
    eiq_manager.validate_feeds(outgoing_feed_id)
    content_blocks = eiq_manager.get_content_blocks(outgoing_feed_id)

    last_max_block_id = read_ids(
        siemplify,
        db_key=str(outgoing_feed_id),
        default_value_to_return="0",
    )
    new_max_block_id = last_max_block_id

    for content_block_url in content_blocks:
        alert_id = str(uuid.uuid4())
        try:
            content_block_id = content_block_url.split("/")[-1]
            if content_block_id <= last_max_block_id:
                continue
            new_max_block_id = max(new_max_block_id, content_block_id)

            eiq_data = eiq_manager.get_content_block_data(content_block_url)
            for data in eiq_data:
                alert_data = fetch_alert(siemplify, data)
                alerts.append(alert_data)
                if is_test_run:
                    break

        except Exception as e:
            siemplify.LOGGER.error(
                f"Failed to process alert {alert_id}",
                alert_id=alert_id,
            )
            siemplify.LOGGER.exception(e)

        if is_test_run:
            break
    write_ids(siemplify, new_max_block_id, db_key=str(outgoing_feed_id))

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
    alert_info.display_id = record_data.get("entity.id")
    alert_info.ticket_id = record_data.get(
        "entity.id",
    )  # In default, ticket_id = display_id. But, if for some reason the external alert id, is different then the composite's key display_id, you can save the original external alert id in this "ticket_id" field.
    alert_info.name = record_data.get("entity.title")
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


def fetch_event(siemplify, record_data):
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
    event["name"] = record_data.get("value")
    event["type"] = record_data.get("type")
    event["device_product"] = (
        PRODUCT  # ie: "device_product" is the field name in arcsight that describes the product the event originated from.
    )
    # ----------------------------- ---------------
    # You are not expected to fill them yourself, just pass them along from the siem. Since this is a dummy generator, We create them manaualy with made up name (PascalCase\CcmelCase doesn't matter)
    observable_type = record_data.get("type").upper()

    event["EIQ_RawJson"] = json.dumps(record_data)
    event["EIQ_Description"] = record_data.get("entity.description")
    event["EIQ_Source"] = record_data.get("source.names")
    event["EIQ_EntityTitle"] = record_data.get("entity.title")
    event["EIQ_PlatformURL"] = record_data.get("meta.entity_url")
    event["EIQ_Labels"] = record_data.get("meta.tags")
    event["EIQ_Confidence"] = record_data.get("meta.confidence")
    event["EIQ_Severity"] = record_data.get("EIQ_severity")
    event["EIQ_Created"] = record_data.get("created")
    event["EIQ_Modified"] = record_data.get("modified")
    event["EIQ_ValidFrom"] = record_data.get("valid_from")
    event[f"EIQ_{observable_type}"] = record_data.get("value")
    return event


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
