"""Luminar IOCs and Leaked Credentials Connector:
 To fetch Luminar IOCs and Leaked Credentials from Luminar API and to store into the
Siemplify platform.
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime
from functools import partial
from itertools import groupby

import requests
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now

from ..core.LuminarManager import (
    LuminarManager,
    enrich_incident_items,
    enrich_malware_items,
    generic_item_finder,
    slice_list_to_max_sub_lists,
)

CONNECTOR_NAME = "Luminar IOCs and Leaked Credentials"
VENDOR = "Cognyte"
PRODUCT = "Luminar IOCs and Leaked Credentials"
RULE_GENERATOR = "Luminar IOCs and Leaked Credentials"
INDICATOR_MAPPING = {
    "DIR": "FileName",
    "MAC": "Mac Address",
    "DOMAIN": "Domain",
    "EMAIL": "Email Address",
    "URL": "URL",
    "IP": "IP Address",
    "SHA512": "FileHash",
    "SHA256": "FileHash",
    "MD5": "FileHash",
    "SHA1": "FileHash",
    "File_Extension": "FileName",
    "File_Size": "FileName",
}
TIMEOUT = 60.0
MAX_IOCS_PER_MALWARE_CASE_EVENT = 500


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
    account_id = siemplify.extract_connector_param(
        "Luminar API Account ID",
        default_value=None,
        input_type=str,
        is_mandatory=True,
        print_value=False,
    )
    client_id = siemplify.extract_connector_param(
        "Luminar API Client ID",
        default_value=None,
        input_type=str,
        is_mandatory=True,
        print_value=False,
    )
    client_secret = siemplify.extract_connector_param(
        "Luminar API Client Secret",
        default_value=None,
        input_type=str,
        is_mandatory=True,
        print_value=False,
    )

    base_url = siemplify.extract_connector_param(
        "Luminar Base URL",
        default_value=None,
        input_type=str,
        is_mandatory=True,
        print_value=False,
    )

    def luminar_api_test_connectivity():
        """Test connection with Siemplify Luminar server"""
        return LuminarManager(
            siemplify,
            client_id,
            client_secret,
            account_id,
            base_url,
        ).test_connectivity()

    def luminar_access_token():
        """Get Luminar access token
        :return: {str} access token
        """
        access_token = LuminarManager(
            siemplify,
            client_id,
            client_secret,
            account_id,
            base_url,
        ).get_access_token()
        return access_token

    siemplify.LOGGER.info("------------------- Main - Started -------------------")
    try:
        time_stamp = siemplify.fetch_timestamp(datetime_format=False)
        if time_stamp:
            time_stamp = int(time_stamp / 1000)
        else:
            time_stamp = 0
        params = {"limit": 100, "offset": 0, "timestamp": time_stamp}
        if is_test_run:
            # only 3 alerts will be created if test run
            params = {"limit": 3, "offset": 0, "timestamp": 0}
        # while loop will iterate until getting all data
        while True:
            return_value, _, _ = luminar_api_test_connectivity()
            if (
                not (account_id and client_id and client_secret and base_url)
                or not return_value
            ):
                siemplify.LOGGER.info(
                    "Please enter Luminar API Credentials and try again.",
                )
                break
            if not luminar_access_token():
                siemplify.LOGGER.info(
                    "Please check Luminar API Credentials, unable to get valid access token from Luminar Server.",
                )
                break
            response = requests.get(
                base_url + "/externalApi/stix",
                params=params,
                headers={"Authorization": f"Bearer {luminar_access_token()}"},
                timeout=TIMEOUT,
            )
            # getting Luminar data page wise
            if "offset" in params:
                params["offset"] = params["offset"] + params["limit"]

            response_json = response.json()

            all_objects = response_json.get("objects", [])
            if is_test_run:
                luminar_api_fetch(siemplify, all_objects, alerts)
                break

            if not all_objects or len(all_objects) == 1:
                siemplify.save_timestamp(new_timestamp=unix_now())
                break
            luminar_api_fetch(siemplify, all_objects, alerts)

    except Exception as err:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {err}")
        siemplify.LOGGER.exception(err)
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(alerts)


def luminar_iocs(siemplify, parent, children, alerts):
    """Enriched unique IOCs sliced into sublist will have max size of 499
    :param parent: {dict} malware dict
    :param children: {dict} indicator dict
    :param alerts: {[]} Enriched unique IOCs appending to the alerts
    """
    try:
        parent, modified_childrens = enrich_malware_items(parent, children)
        # Slicing IOCs to sublist
        for ioc_chunks in list(
            slice_list_to_max_sub_lists(
                # filtering unique leaked records based on indicator_value
                list(
                    {
                        item["indicator_value"]: item
                        for item in modified_childrens
                        if item.get("indicator_value")
                    }.values(),
                ),
                MAX_IOCS_PER_MALWARE_CASE_EVENT - 1,
            ),
        ):
            if fetch_alert_ioc(siemplify, ioc_chunks, parent["name"], "Malware_Family"):
                # fetching alerts
                alerts.append(
                    fetch_alert_ioc(
                        siemplify,
                        ioc_chunks,
                        parent["name"],
                        "Malware_Family",
                    ),
                )
    except Exception as err:
        siemplify.LOGGER.error(f"Got exception on luminar_iocs. Error: {err}")
        siemplify.LOGGER.exception(err)


def luminar_leaked(siemplify, parent, children, alerts):
    """Enriched unique incidents sliced into sublist will have max size of 499
    :param parent: {dict} incident dict
    :param children: {dict} user account dict
    :param alerts: {[]} Enriched unique incident appending to the alerts
    """
    try:
        parent, modified_childrens = enrich_incident_items(parent, children)
        # Slicing leaked records to sublist
        for ioc_chunks in list(
            slice_list_to_max_sub_lists(
                # filtering unique leaked records based on display_name
                list(
                    {
                        item["display_name"]: item for item in modified_childrens
                    }.values(),
                ),
                MAX_IOCS_PER_MALWARE_CASE_EVENT - 1,
            ),
        ):
            if fetch_alert_leaked_credentials(
                siemplify,
                ioc_chunks,
                parent.get("name"),
                "Incident_Name",
            ):
                alerts.append(
                    # fetching alerts
                    fetch_alert_leaked_credentials(
                        siemplify,
                        ioc_chunks,
                        parent.get("name"),
                        "Incident_Name",
                    ),
                )
    except Exception as err:
        siemplify.LOGGER.error(f"Got exception on luminar_leaked. Error: {err}")
        siemplify.LOGGER.exception(err)


def luminar_expiration_iocs(siemplify, all_objects, alerts):
    """Enriched unique IOCs sliced into sublist will have max size of 499.
    grouped the IOCs based on the expiration date.
    :param all_objects: {[]} all object is a list which contain all dict like malware,incident,incidents
    :param alerts: {[]} Enriched unique incident appending to the alerts
    """
    try:
        # Fetching only IOCs which has an expiration date and expiration date greater than or equal to the current date.
        _, exp_iocs = enrich_malware_items(
            {},
            list(
                filter(
                    lambda x: (
                        x.get("type") == "indicator"
                        if x.get("valid_until")
                        and datetime.strptime(
                            (x.get("valid_until"))[:19],
                            "%Y-%m-%dT%H:%M:%S",
                        )
                        >= datetime.today()
                        else None
                    ),
                    all_objects,
                ),
            ),
        )
        # Grouping IOCs based on an expiration date
        if exp_iocs:
            for date, exp_iocs_datewise in groupby(
                sorted(
                    list({item["indicator_value"]: item for item in exp_iocs}.values()),
                    key=lambda d: d["valid_until"],
                ),
                lambda x: datetime.strptime((x.get("valid_until"))[:10], "%Y-%m-%d"),
            ):
                # Slicing IOCs to sublist
                for iocs in list(
                    slice_list_to_max_sub_lists(
                        list(exp_iocs_datewise),
                        MAX_IOCS_PER_MALWARE_CASE_EVENT - 1,
                    ),
                ):
                    if fetch_alert_ioc(
                        siemplify,
                        iocs,
                        date.strftime("%Y-%m-%d"),
                        "Expiration_Date",
                    ):
                        alerts.append(
                            # fetching alerts
                            fetch_alert_ioc(
                                siemplify,
                                iocs,
                                date.strftime("%Y-%m-%d"),
                                "Expiration_Date",
                            ),
                        )

    except Exception as err:
        siemplify.LOGGER.error(
            f"Got exception on luminar_expiration_iocs. Error: {err}",
        )
        siemplify.LOGGER.exception(err)


def luminar_api_fetch(siemplify, all_objects, alerts):
    """Segregating IOCs or Leaked Credentials List based on Malware/Incident.
    :param all_objects: {[]} all object is a list which contain all dict like malware,incident,incidents
    :param alerts: {[]} list to append IOCs/Incident data
    """
    try:
        get_item_by_id = partial(generic_item_finder, all_objects)
        luminar_expiration_iocs(siemplify, all_objects, alerts)
        relationships = {}
        # Filtering relationship dict from all objects
        for relationship in filter(
            lambda x: x.get("type") == "relationship",
            all_objects,
        ):
            relationship_items = relationships.get(relationship.get("target_ref"), [])

            relationship_items.append(relationship.get("source_ref"))

            relationships[relationship["target_ref"]] = relationship_items

        for key, group in relationships.items():
            parent = next(get_item_by_id(key), None)
            children = list(
                filter(
                    None,
                    [next(get_item_by_id(item_id), None) for item_id in group],
                ),
            )
            if parent and parent.get("type") == "malware":
                luminar_iocs(siemplify, parent, children, alerts)
            elif parent and parent.get("type") == "incident":
                luminar_leaked(siemplify, parent, children, alerts)
    except Exception as err:
        siemplify.LOGGER.error(f"Got exception on luminar_api_fetch. Error: {err}")
        siemplify.LOGGER.exception(err)


def fetch_alert_leaked_credentials(siemplify, alert, name, name_type):
    """Returns an alert, which is an aggregation of Leaked Credentials events."""
    try:
        alert_info = AlertInfo()
        alert_info.display_id = str(uuid.uuid4())
        alert_info.ticket_id = str(uuid.uuid4())
        alert_info.rule_generator = RULE_GENERATOR
        alert_info.start_time = unix_now()
        alert_info.end_time = unix_now()
        alert_info.name = name + "  " + name_type
        alert_info.priority = 100
        alert_info.device_vendor = VENDOR
        alert_info.device_product = PRODUCT
        alert_info.environment = siemplify.context.connector_info.environment
        for events in alert:
            try:
                event_info = fetch_event_leaked_credentials(events)
                if event_info:
                    alert_info.events.append(event_info)
            except Exception as err:
                siemplify.LOGGER.error(f"Got exception on alert_id. Error: {err}")
                siemplify.LOGGER.exception(err)
        siemplify.LOGGER.info(f"Alert {alert_info.ticket_id} was created.")
        return alert_info
    except Exception as err:
        siemplify.LOGGER.error(
            f"Got exception on fetch_alert_leaked_credentials. Error: {err}",
        )
        siemplify.LOGGER.exception(err)


def fetch_event_leaked_credentials(events):
    """Returns an event, which is an aggregation of Leaked Credentials details."""
    event = {}
    event["StartTime"] = unix_now()
    event["EndTime"] = unix_now()
    event["luminar_case_name"] = "Luminar Leaked Credentials"
    event["name"] = events.get("display_name")
    event["device_product"] = PRODUCT
    event["event_type"] = "Leaked " + events.get("display_name")
    event["display_name"] = events.get("display_name")
    event["credentials"] = events.get("credential")
    event["incident_creation_date"] = events.get("created")
    event["incident_modified_date"] = events.get("modified")
    event["incident_description"] = (
        events.get("description") if events.get("description") else ""
    )
    event["account_login"] = events.get("account_login")
    event["incident_name"] = events.get("name")
    return event


def fetch_alert_ioc(siemplify, alert, name, name_type):
    """Returns an alert, which is an aggregation of IOCs."""
    alert_info = AlertInfo()
    alert_info.display_id = str(uuid.uuid4())
    alert_info.ticket_id = str(uuid.uuid4())
    alert_info.name = name + "  " + name_type
    alert_info.rule_generator = RULE_GENERATOR
    alert_info.start_time = unix_now()
    alert_info.end_time = unix_now()
    alert_info.priority = 100
    alert_info.device_vendor = VENDOR
    alert_info.device_product = PRODUCT
    alert_info.environment = siemplify.context.connector_info.environment
    if alert:
        for events in alert:
            try:
                if events.get("indicator_type"):
                    event_info = fetch_event_ioc(events)
                    if event_info:
                        alert_info.events.append(event_info)
            except Exception as err:
                siemplify.LOGGER.error(
                    f"Got exception on fetch_alert_ioc. Error: {err}",
                )
                siemplify.LOGGER.exception(err)
    siemplify.LOGGER.info(f"Alert {alert_info.ticket_id} was created.")
    return alert_info


def fetch_event_ioc(events):
    """Returns an event, which is an aggregation of Leaked Credentials details."""
    event = {}
    event["indicator_expiration_date"] = events.get("valid_until", "")
    event["StartTime"] = unix_now()
    event["EndTime"] = unix_now()
    event["luminar_case_name"] = "Luminar IOCs"
    event["device_product"] = PRODUCT
    malware_details = events.get("malware_details")
    event["indicator_type"] = events.get("indicator_type")
    if events.get("indicator_type") in INDICATOR_MAPPING:
        event[INDICATOR_MAPPING[events.get("indicator_type")]] = events.get(
            "indicator_value",
        )
    event["name"] = events.get("indicator_value")
    event["event_type"] = "Malicious " + events.get("indicator_type")
    event["malware_types"] = (
        ",".join(malware_details.get("malwareTypes"))
        if malware_details.get("malwareTypes")
        else ""
    )
    event["malware_family"] = (
        malware_details.get("name") if malware_details.get("name") else ""
    )
    event["indicator_created_date"] = events.get("created")
    event["indicator_value"] = events.get("indicator_value")
    event["malware_created_date"] = (
        malware_details.get("created") if malware_details else ""
    )
    event["malware_modified_date"] = (
        malware_details.get("modified") if malware_details else ""
    )
    return event


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
