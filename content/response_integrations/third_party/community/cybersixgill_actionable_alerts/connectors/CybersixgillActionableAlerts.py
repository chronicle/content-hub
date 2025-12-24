from __future__ import annotations

import datetime
import json
import sys
import traceback
from datetime import datetime, timedelta

from sixgill.sixgill_actionable_alert_client import SixgillActionableAlertClient
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now

CONNECTOR_NAME = "Cybersixgill Actionable Alerts"
VENDOR = "Cybersixgill"
PRODUCT = "Cybersixgill Actionable Alerts"
RULE_GENERATOR_EXAMPLE = "Cybersixgill Actionable Alerts"
SIXGILL_CHANNEL_ID = "1f4fdd520d3a721799fc0d044283d364"
Alerts_Time_Format = "%Y-%m-%d %H-%M-%S"


def fetch_alert(alert_data, sixgill_client, org_id):
    """Returns an alert, which is an aggregation of basic events.
    (ie: Arcsight's correlation, QRadar's Offense)
    """
    alert_info = AlertInfo()
    alert_info.display_id = alert_data.get("id")
    alert_info.ticket_id = alert_data.get("id")
    alert_info.name = alert_data.get("title")
    alert_info.rule_generator = RULE_GENERATOR_EXAMPLE
    alert_info.start_time = unix_now()
    alert_info.end_time = unix_now()
    if alert_data.get("threat_level") == "imminent":
        priority = 100
    else:
        priority = 80
    alert_info.priority = (
        priority  # Informative = -1,Low = 40,Medium = 60,High = 80,Critical = 100.
    )
    alert_info.device_vendor = VENDOR
    alert_info.device_product = PRODUCT
    alert_event = fetch_event(alert_data, sixgill_client, org_id)
    alert_info.events.append(alert_event)
    return alert_info


def fetch_event(alert_data, sixgill_client, org_id):
    global created_time_last_alert
    event = {}
    alert_id = alert_data.get("id")
    portal_url = f"https://portal.cybersixgill.com/#/?actionable_alert={alert_id}"
    alerts_info = sixgill_client.get_actionable_alert(alert_id, organization_id=org_id)
    additional_info = alerts_info.get("additional_info", {})
    event["Alert_RawJson"] = json.dumps(alerts_info)
    event["StartTime"] = unix_now()
    event["EndTime"] = unix_now()
    event["device_product"] = PRODUCT
    event["Alert_Name"] = alert_data.get("title")
    event["Alert_Id"] = alert_id
    event["Portal_URL"] = portal_url
    event["Description"] = alerts_info.get("description")
    event["Content"] = alerts_info.get("content")
    event["Create_Time"] = alerts_info.get("create_time")
    created_time_last_alert = alerts_info.get("create_time")
    attributes = additional_info.get("asset_attributes", [])
    attributes = ", ".join(attributes)
    if attributes:
        event["Attributes"] = attributes
    event["Threat_Level"] = alerts_info.get("threat_level", "Unknown")
    threats = additional_info.get("threats", [])
    threats = ", ".join(threats)
    if threats:
        event["Threat_Type"] = threats
    event["Assessment"] = alerts_info.get("assessment", None)
    recommendations = additional_info.get("recommendations", [])
    recommendations = ", ".join(recommendations)
    if recommendations:
        event["Recommendations"] = recommendations
    alert_description = (
        "<html><head><style>table, th, td {border: 1px solid black;border-collapse:"
        "collapse;}</style></head><body><h2>Sub Alerts</h2></body></html>"
    )
    event["Sub_Alerts"] = alert_description
    sub_alerts = alert_data.get("sub_alerts", [])
    if sub_alerts:
        for sub in sub_alerts:
            alert_description += (
                f"<html><table style='width:100%'><tr><td>Aggregate Alert ID</td>"
                f"<td>{sub.get('aggregate_alert_id')}</td></tr>"
                f"<tr><td>Content</td><td>{sub.get('content')}</td></tr>"
                f"<tr><td>Date</td><td>{sub.get('date')}</td></tr>"
                f"<tr><td>Matched Assets</td><td>{sub.get('matched_assets')}</td></tr>"
                f"<tr><td>Site</td><td>{sub.get('site')}</td></tr></table><br></html>"
            )
        event["Sub_Alerts"] = alert_description
    if "cve_id" in additional_info:
        cve_portal = (
            f"https://portal.cybersixgill.com/#/cve/{additional_info.get('cve_id', '')}"
        )
        cvss_3 = additional_info.get("nvd", {}).get("v3", {}).get("current")
        cvss_2 = additional_info.get("nvd", {}).get("v2", {}).get("current")
        dve_score = additional_info.get("score", {}).get("current")
        event["CVE_Portal_URL"] = cve_portal
        event["CVSS_3_1"] = cvss_3
        event["CVSS_2_0"] = cvss_2
        event["DVE_Score"] = dve_score
        event["CVE_ID"] = additional_info.get("cve_id")
        attributes = []
        attributes_dict = {}
        for att in additional_info.get("attributes"):
            if att.get("value"):
                attributes_dict["Name"] = att.get("name")
                attributes_dict["Description"] = att.get("description")
                attributes.append(attributes_dict)
        event["CVE_Attributes"] = json.dumps({"CVE_Attributes": attributes})
    return event


def create_sixgill_client_obj(siemplify, client_id, client_secret, channel_id):
    """This create a sixgill client object
    Returns:
        sixgill.sixgill_feed_client.SixgillFeedClient -- Sixgill Client object
    """
    try:
        sixgill_alerts_client = SixgillActionableAlertClient(
            client_id,
            client_secret,
            channel_id,
            logger=siemplify.LOGGER,
            verify=True,
        )
        return sixgill_alerts_client
    except Exception as err:
        siemplify.LOGGER.error("create_sixgill_client_obj - Error - " + str(err))
        siemplify.LOGGER.info(traceback.format_exc())


def query_sixgill(
    siemplify,
    sixgill_alerts_client,
    limit_size,
    from_date,
    to_date,
    threat_level,
    threat_type,
    org_id,
):
    try:
        if threat_type:
            threat_types_list = threat_type.split(",")
        else:
            threat_types_list = None
        if not threat_level:
            threat_level = None
        alerts_list = sixgill_alerts_client.get_actionable_alerts_bulk(
            from_date=from_date,
            to_date=to_date,
            limit=limit_size,
            threat_level=threat_level,
            threat_type=threat_types_list,
            sort_order="asc",
            organization_id=org_id,
        )
        return alerts_list
    except Exception as err:
        siemplify.LOGGER.error(err)
        siemplify.LOGGER.error(traceback.format_exc())


def datetime_params(siemplify):
    try:
        current_time = datetime.now()
        fetch_time = siemplify.fetch_timestamp(datetime_format=True, timezone=False)
        fetch_str = datetime.strftime(fetch_time, Alerts_Time_Format)
        fetch_stamp = datetime.strptime(fetch_str, Alerts_Time_Format)
        if fetch_stamp.year == 1970:
            days_back = siemplify.extract_connector_param(
                "Days Back On First Run ",
                default_value=30,
                input_type=int,
            )
            from_datetime = current_time
            str_from_date = from_datetime.strftime(Alerts_Time_Format)
            str_from_date = datetime.strptime(str_from_date, Alerts_Time_Format)
            from_time = str_from_date - timedelta(days=days_back)
        else:
            from_time = fetch_stamp
        to_time = current_time
        str_to_date = to_time.strftime(Alerts_Time_Format)
        to_time = datetime.strptime(str_to_date, Alerts_Time_Format)
        return from_time, to_time
    except Exception as err:
        siemplify.LOGGER.error(err)
        siemplify.LOGGER.error(traceback.format_exc())


@output_handler
def main(is_test_run):
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_NAME
    alerts = []
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
    )
    client_secret = siemplify.extract_connector_param(
        "Client Secret",
        default_value=None,
        input_type=str,
        is_mandatory=True,
    )
    limit_size = siemplify.extract_connector_param(
        "Alerts Limit",
        default_value=None,
        input_type=int,
        is_mandatory=True,
    )
    threat_level = siemplify.extract_connector_param(
        "Threat Level",
        default_value=None,
        input_type=str,
    )
    threat_type = siemplify.extract_connector_param(
        "Threat Type",
        default_value=None,
        input_type=str,
    )
    org_id = siemplify.extract_connector_param(
        "Organization id",
        default_value=None,
        input_type=str,
    )
    siemplify.LOGGER.info("------------------- Main - Started -------------------")
    sixgill_client = create_sixgill_client_obj(
        siemplify,
        client_id,
        client_secret,
        SIXGILL_CHANNEL_ID,
    )
    from_date, to_date = datetime_params(siemplify)
    records = query_sixgill(
        siemplify,
        sixgill_client,
        limit_size,
        from_date,
        to_date,
        threat_level,
        threat_type,
        org_id,
    )
    siemplify.LOGGER.info("True")
    if records:
        for rec in records:
            try:
                alert_data = fetch_alert(rec, sixgill_client, org_id)
                if alert_data:
                    alerts.append(alert_data)
            except Exception as e:
                siemplify.LOGGER.exception(e)
        last_alert_time = datetime.strptime(
            created_time_last_alert,
            "%Y-%m-%d %H:%M:%S",
        )
        siemplify.save_timestamp(
            datetime_format=True,
            timezone=False,
            new_timestamp=last_alert_time,
        )
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(alerts)


if __name__ == "__main__":
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
