from __future__ import annotations

import json
import re
import sys

import requests
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import (
    convert_datetime_to_unix_time,
    convert_string_to_datetime,
    output_handler,
)

CONNECTOR_NAME = "beSECURE Connector"
VENDOR = "Beyond Security"
PRODUCT = "beSECURE"
beSECURE_RULE = "Pull High/Medium and Low Vulnerabilities"


@output_handler
def main(is_test_run):
    alerts = []  # The main output of each connector run
    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******',
        )

    siemplify.LOGGER.info("==================== Main - Param Init ====================")

    api_key = siemplify.extract_connector_param(
        "API Key",
        default_value="",
        input_type=str,
        is_mandatory=False,
        print_value=False,
    )
    api_key = re.sub(r"[^A-Z0-9\-]", "", api_key)  # Clean non-API related characters

    # URL can be https://... http://... https://hostname:port/ https://hostname/someprefix
    url = siemplify.extract_connector_param(
        "URL",
        default_value="",
        input_type=str,
        is_mandatory=False,
        print_value=False,
    )
    if not url.startswith("https://") and not url.startswith("http://"):
        url = "https://" + url

    rotation_time = siemplify.extract_connector_param(
        "Check Every X Minutes",
        default_value=15,
        input_type=int,
        is_mandatory=False,
        print_value=False,
    )
    verify_ssl = siemplify.extract_connector_param(
        "Verify SSL Ceritifcate?",
        default_value=False,
        input_type=bool,
        is_mandatory=False,
        print_value=False,
    )

    siemplify.LOGGER.info("------------------- Main - Started -------------------")

    siemplify.LOGGER.info(
        f"Pull scans that have finished in the past {rotation_time} minutes",
    )
    # /json.cgi?primary=admin&secondary=networks&action=returnnetworks&search_limit=10&&search_datelastscanned_value=15&search_datelastscanned_type=minute
    scans = make_action(
        siemplify,
        url,
        verify_ssl,
        primary="admin",
        secondary="networks",
        action="returnnetworks",
        apikey=api_key,
        search_limit=10000,
        search_datelastscanned_value=rotation_time,
        search_datelastscanned_type="year",
    )

    # siemplify.LOGGER.info("scans: {}".format(scans))
    if "error" in scans:
        siemplify.LOGGER.info(f"An error has occured: {scans['error']}")
        return None

    if scans["count"] == 0:
        siemplify.LOGGER.info(f"No scans finished in past {rotation_time} minutes")
        return siemplify.return_package(alerts)

    previous_scans = {}
    try:
        with open("previous_scans.json") as json_file:
            previous_scans = json.load(json_file)
    except Exception:
        siemplify.LOGGER.info(
            "previous_scans.json is missing, this is expected when you run the connector the first time",
        )

    ###
    # If we have results - i.e. scans that finished, pull the information
    for scan in scans["data"]:
        networkid = scan["ID"]

        siemplify.LOGGER.info(f"Pulling JSON results for scan ID: {networkid}")
        result = make_action(
            siemplify,
            url,
            verify_ssl,
            primary="vulnerabilities",
            secondary="report",
            action="getreport",
            format="json",
            network=networkid,
            reporttype="regular",
            apikey=api_key,
        )

        if (
            "Scan" not in result
            or "ScanDetails" not in result["Scan"]
            or "ScanDate" not in result["Scan"]["ScanDetails"]
        ):
            continue

        # siemplify.LOGGER.info("ScanDetails: {}".format(result['Scan']['ScanDetails']))
        scannumber = result["Scan"]["ScanDetails"]["MaxScanNumber"]
        if f"{networkid}-{scannumber}" in previous_scans:
            siemplify.LOGGER.info(
                f"Already processed results for scan: {networkid} and scan number: {scannumber}",
            )
            continue

        previous_scans[f"{networkid}-{scannumber}"] = 1

        scan_date = result["Scan"]["ScanDetails"]["ScanDate"]
        siemplify.LOGGER.info(f"scan_date: {scan_date}")

        # siemplify.LOGGER.info("result: {}".format(result))
        vulnerableHosts = []

        if ("VulnerableHosts" in result) and (
            "VulnerableHost" in result["VulnerableHosts"]
        ):
            if type(result["VulnerableHosts"]["VulnerableHost"]) is list:
                vulnerableHosts = result["VulnerableHosts"]["VulnerableHost"]
            if type(result["VulnerableHosts"]["VulnerableHost"]) is dict:
                vulnerableHosts.append(result["VulnerableHosts"]["VulnerableHost"])

        count = 0
        for vulnerableHost in vulnerableHosts:
            # siemplify.LOGGER.info("vulnerableHost: {}".format(vulnerableHost))
            # siemplify.LOGGER.info("RiskFactor: {}".format( vulnerableHost['Vulnerability']['RiskFactor'] ))

            if (
                "Vulnerability" not in vulnerableHost
                or "RiskFactor" not in vulnerableHost["Vulnerability"]
                or int(vulnerableHost["Vulnerability"]["RiskFactor"]) < 1
            ):
                continue

            # siemplify.LOGGER.info("Processing: {}".format( vulnerableHost['VulnID'] ))

            new_alert = create_alert(siemplify, vulnerableHost, scan_date)
            if new_alert is not None:
                count += 1
                alerts.append(new_alert)

        siemplify.LOGGER.info(f"inserted {count} alerts")

    with open("previous_scans.json", "w") as outfile:
        json.dump(previous_scans, outfile)

    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(alerts)


def create_alert(siemplify, vulnerableHost, scan_date):
    siemplify.LOGGER.info(
        f"-------------- Started processing vulnerability {vulnerableHost['VulnID']}",
    )
    alert_info = AlertInfo()

    if "VulnID" not in vulnerableHost:
        return None

    alert_info.display_id = vulnerableHost["VulnID"]
    alert_info.ticket_id = vulnerableHost[
        "VulnID"
    ]  # In default, ticket_id = display_id. But, if for some reason the external alert id, is different then the composite's key display_id, you can save the original external alert id in this "ticket_id" field.

    if (
        "Vulnerability" not in vulnerableHost
        or "Name" not in vulnerableHost["Vulnerability"]
        or "Name" not in vulnerableHost
        or "StrPort" not in vulnerableHost
    ):
        return None

    alert_info.name = f"{vulnerableHost['Vulnerability']['Name']} on {vulnerableHost['Name']} via port {vulnerableHost['StrPort']}"
    alert_info.rule_generator = beSECURE_RULE  # Describes the name of the siem's rule, that caused the aggregation of the alert.
    alert_info.start_time = convert_datetime_to_unix_time(
        convert_string_to_datetime(scan_date + " UTC"),
    )  # Times should be saved in UnixTime. You may use SiemplifyUtils.convert_datetime_to_unix_time, or SiemplifyUtils.convert_string_to_datetime
    alert_info.end_time = convert_datetime_to_unix_time(
        convert_string_to_datetime(scan_date + " UTC"),
    )  # Times should be saved in UnixTime. You may use SiemplifyUtils.convert_datetime_to_unix_time, or SiemplifyUtils.convert_string_to_datetime

    alert_info.priority = (
        -1
    )  # Informative = -1,Low = 40,Medium = 60,High = 80,Critical = 100.

    if "RiskFactor" not in vulnerableHost["Vulnerability"]:
        return None

    if vulnerableHost["Vulnerability"]["RiskFactor"] == 1:
        alert_info.priority = 40
    if vulnerableHost["Vulnerability"]["RiskFactor"] == 4:
        alert_info.priority = 60
    if vulnerableHost["Vulnerability"]["RiskFactor"] == 8:
        alert_info.priority = 80

    alert_info.device_vendor = VENDOR  # This field, may be fetched from the Original Alert. If you build this alert manualy, Describe the source vendor of the data. (ie: Microsoft, Mcafee)
    alert_info.device_product = PRODUCT

    new_event = create_event(
        siemplify,
        alert_info.display_id,
        alert_info.display_id,
        vulnerableHost,
        scan_date,
    )
    if new_event is not None:
        alert_info.events.append(new_event)

    return alert_info


def create_event(siemplify, alert_id, event_id, vulnerableHost, scan_date):
    # siemplify.LOGGER.info("--- Started processing Event:  alert_id: {} | event_id: {}".format(alert_id, event_id))
    event = {}

    """
HostID: "81F84FB5"
Name: "1.1.1.1"
Port: "445"
Proto: "tcp"
Service: "microsoft-ds"
StrPort: "microsoft-ds (445/tcp)"
VulnID: "7970"
Vulnerability: {DynamicOutput: {}, Family: "Preliminary Analysis", FamilyID: "17", Impact: {}, Name: "Open Port", ...}
  DynamicOutput: {}
  Family: "Preliminary Analysis"
  FamilyID: "17"
  Impact: {}
  Name: "Open Port"
  Output: {}
  RiskFactor: "0"
  Solution: {}
  Summary: {}
  SummaryOriginal: {}
  Test: {Added: "2000-01-01", Revision: "1", TestID: "719", TestType: "0"}
    Added: "2000-01-01"
    Revision: "1"
    TestID: "719"
    TestType: "0"
  Ticket: {CommentLog: {}, ID: {}}
    CommentLog: {}
    ID: {}
  """

    if (
        "Vulnerability" not in vulnerableHost["Vulnerability"]
        or "Name" not in vulnerableHost["Vulnerability"]
        or "StrPort" not in vulnerableHost
        or "Name" not in vulnerableHost
        or "Service" not in vulnerableHost
        or "HostID" not in vulnerableHost
        or "Family" not in vulnerableHost
        or "Test" not in vulnerableHost["Vulnerability"]
        or "TestID" not in vulnerableHost["Vulnerability"]["Test"]
    ):
        return None

    event["HostID"] = vulnerableHost["HostID"]  # Unique identifier of the remote host
    event["Port"] = vulnerableHost["Port"]  # Affected Port (on tested target)
    event["Category"] = vulnerableHost["Family"]  # Test Category
    event["TestID"] = vulnerableHost["Vulnerability"]["Test"][
        "TestID"
    ]  # The Test Identifier

    # ----------- Mandatory Fields ---------------
    # A valid event must have a "Start Time", "End Time", "Name", and "Device Product". Their name is not important (What ever it is, it will be mapped).
    # ie: "Start Time" may be called "Start Time", "StartTime", "start_time", "johnDoeStartTime"
    event["StartTime"] = convert_datetime_to_unix_time(
        convert_string_to_datetime(scan_date + " UTC"),
    )
    event["EndTime"] = convert_datetime_to_unix_time(
        convert_string_to_datetime(scan_date + " UTC"),
    )
    event["name"] = (
        f"{vulnerableHost['Vulnerability']['Name']} on {vulnerableHost['Name']} via port {vulnerableHost['StrPort']}"
    )
    event["device_product"] = vulnerableHost["Service"]

    # ----------------------------- ---------------

    # usually, the most intresting fields are (again, their precise name, may vary between siems.
    # You are not expected to fill them yourself, just pass them along from the siem. Since this is a dummy generator, We create them manaualy with made up name (PascalCase\CcmelCase doesn't matter)
    # event["SourceHostName"] = vulnerableHost['Name']
    event["DestinationHostName"] = vulnerableHost["Name"]
    # event["SourceAddress"] = "10.0.0."+str(randrange(254))

    event["DestinationAddress"] = vulnerableHost["Name"]

    # siemplify.LOGGER.info("--- Finished processing Event: alert_id: {} | event_id: {}".format(alert_id, event_id))

    return event


def make_action(siemplify, url, verify_ssl, **kwargs):
    params = dict([(k, v) for k, v in list(kwargs.items())])

    siemplify.LOGGER.info(
        f"Sending request to [{url}] with:\n{json.dumps(params, indent=2)}",
    )

    data = requests.get(f"{url}/json.cgi", params=params, verify=verify_ssl).json()

    return data


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
