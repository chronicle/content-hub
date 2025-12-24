from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Callable, Optional, Sequence

import requests
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo

if TYPE_CHECKING:
    from soar_sdk.SiemplifyAction import SiemplifyAction
    from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution

from ..core.constants import (
    THINKST_CONTEXT_IDENTIFIER,
    THINKST_FALLBACK_TIME_MINS,
    THINKST_LAST_TIMESTAMP,
    THINKST_OPERATIONAL_LOGTYPES,
    THINKST_PRODUCT,
    THINKST_UPDATE_KEY,
    THINKST_VENDOR,
)

PRIORITY_INFO = -1
PRIORITY_LOW = 40
PRIORITY_MED = 60
PRIORITY_HIGH = 80
PRIORITY_CRIT = 100

TOKEN_NAME_MAP = {
    "active-directory-login": "Active Directory Login",
    "autoreg-google-docs": "Google Doc",
    "autoreg-google-sheets": "Google Sheet",
    "aws-id": "AWS API Key",
    "aws-s3": "AWS S3 Bucket",
    "azure-entra-login": "Azure Entra Login",
    "azure-id": "Azure Login Certificate and Config",
    "cloned-css": "CSS cloned site",
    "cloned-web": "Cloned Website",
    "credit-card": "Credit Card",
    "dns": "DNS",
    "doc-msexcel": "MS Excel Document",
    "doc-msword": "MS Word Document",
    "fast-redirect": "Fast Redirect",
    "gmail": "Gmail",
    "google-docs": "Google Doc",
    "google-sheets": "Google Sheet",
    "http": "Web Bug",
    "idp-app": "IdP App",
    "msexcel-macro": "MS Excel Macro Document",
    "msword-macro": "MS Word Macro Document",
    "mysql-dump": "MySQL Dump",
    "office365mail": "Office 365 Mail Bug",
    "pdf-acrobat-reader": "Acrobat PDF",
    "pwa": "Fake App",
    "qr-code": "QR Code",
    "sensitive-cmd": "Sensitive Command",
    "signed-exe": "Custom Exe/Binary",
    "slack-api": "Slack API Key",
    "slow-redirect": "Slow Redirect",
    "web-image": "Custom Web Image",
    "windows-dir": "Windows Folder",
    "wireguard": "WireGuard VPN",
}


class ThinkstManager:
    """
    This is provides the base requests session and api_get/api_post
    functionality to talk to the Canry Console. It is expected to be subclassed
    for the Actions and Connector specific implementation.
    """
    def __init__(
        self,
        api_key: str,
        console_hash: str,
        siemplify: SiemplifyAction | SiemplifyConnectorExecution,
        verify_ssl: bool = True,
    ) -> None:
        """
        Initialise the ThinkstManager

        Args:
            api_key: api_key of the Canary Console
            console_hash: The domain name of Canary Console (the part before canary.tools)
            siemplify: The specific siemplify object this uses
            verify_ssl: Whether to ignore ssl errors or not
        """
        self.api_key = api_key
        self.console_hash = console_hash
        self.siemplify = siemplify

        # Just so we have bit of a shorter path to call the logger
        self.logger = siemplify.LOGGER

        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.params = {"auth_token": api_key}

        self.console_url = f"https://{self.console_hash}.canary.tools"
        self.api_base_url = f"{self.console_url}/api/v1"

    def api_get_request(self, endpoint: str, params: dict = {}) -> dict[str, Any]:
        """
        Get the json data from the API endpoint

        Args:
            endpoint: The api endpoint URL
            params: Any extra parameters for the request

        Returns:
            Json object

        Raises:
            Generic Exception if status_code != 200
        """
        self.logger.debug(f"api_get_request: {endpoint=}, {params=}")
        response = self.session.get(endpoint, params=params)
        if response.status_code != 200:
            raise Exception(f"Unexpected HTTP {response.status_code}: {response.text}")

        return response.json()

    def api_post_request(self, endpoint: str, params: dict = {}) -> dict[str, Any]:
        """
        Post data to the API endpoint

        Args:
            endpoint: The api endpoint URL
            params: Any extra parameters for the request

        Returns:
            Json object

        Raises:
            Generic Exception if status_code != 200
        """
        self.logger.debug(f"api_post_request: {endpoint=}, {params=}")
        response = self.session.post(endpoint, params=params)
        if response.status_code != 200:
            raise Exception(f"Unexpected HTTP {response.status_code}: {response.text}")

        return response.json()


class ThinkstActionManager(ThinkstManager):
    """
    The Action specific implementation of the ThinkstManager
    """
    def __init__(
        self,
        api_key: str,
        console_hash: str,
        siemplify: SiemplifyAction,
        verify_ssl: bool = True,
    ) -> None:
        super().__init__(
            api_key=api_key,
            console_hash=console_hash,
            siemplify=siemplify,
            verify_ssl=verify_ssl)

    def ping(self) -> bool:
        """
        Call the 'ping' endpoint on the Canary Console

        Returns:
            True if the request succeeded
        """
        api_endpoint = f"{self.api_base_url}/ping"

        ping_res = self.api_get_request(api_endpoint)
        self.logger.debug(f"{ping_res}")

        return ping_res.get("result", "error") == "success"

    def ack_alert(self) -> tuple[Any, str]:
        """
        Acknowledge an alert on the Canary Console

        This grabs the 'security_events' from the current_alert and tries to
        find the "AlertId" which was stashed there when the connector created
        the alert. This is then used to acknowledge the 'incident' on the
        Canary Console

        Returns:
            Tuple of Execution state and an accompanying message
        """
        api_endpoint = f"{self.api_base_url}/incident/acknowledge"
        incident_id = None
        try:
            events = self.siemplify.current_alert.security_events
            if len(events) > 0:
                properties = events[0].additional_properties
                incident_id = properties.get("AlertId")
            else:
                msg = "No events found for alert"
                return (EXECUTION_STATE_FAILED, msg)
        except Exception as e:
            msg = f"Could not get incident information from alert. {e}"
            return (EXECUTION_STATE_FAILED, msg)

        try:
            if incident_id:
                params = {"incident": incident_id}
                resp = self.api_post_request(api_endpoint, params=params)
                if resp.get("result", "") == "success":
                    msg = "Alert acknowledged!"
                    return (EXECUTION_STATE_COMPLETED, msg)
        except Exception as e:
            msg = f"Could not acknowledge incident on Canary Console. {e}"
            return (EXECUTION_STATE_FAILED, msg)

        msg = "Could not acknowledge incident on Canary Console"
        return (EXECUTION_STATE_FAILED, msg)


def get_past_time(minutes: int) -> str:
    """
    Calculate a time X minutes in the past from now

    The return value is in the format expected by the Canary Console API

    Args:
        minutes: How far back to calculate

    Returns:
        A string timestamp, formatted as "%Y-%m-%d-%H:%M:%S"
    """
    now = datetime.utcnow()
    tmp = now - timedelta(minutes=minutes)
    past_time = tmp.strftime("%Y-%m-%d-%H:%M:%S")
    return past_time


def to_unix_milliseconds(timestamp: int | str) -> int:
    """
    Converts a UNIX timestamp (in seconds) to milliseconds.

    Args:
        timestamp: Input UNIX timestamp in seconds as int or string

    Returns:
        UNIX timestamp in milliseconds
    """
    timestamp = int(timestamp)
    return timestamp * 1000


def value_in_ranged_list(in_list: Sequence[int | tuple[int, int]], check_value: int) -> bool:
    """
    Check if value is present in a list (or in range in the list)

    This is used to check if 'check_value' is in a specific set of values
    specified by 'in_list'. 'in_list' can contain normal ints, which can just
    be directly compared, but it can also specify a range of values to compare
    by using a tuple with the start/end values.

    NOTE: The tuples are passed to the 'range' function, so the first value of
    the tuple is INCLUDED, and the last one is EXCLUDED. e.g, (0, 3) will only
    check if 'check_value' is '0', '1', or '2'.

    Args:
        in_list: List containing a mix of ints, or tuples of (int, int)
        check_value: the value to search for in the list

    Returns:
        True if value was found in list, else False
    """
    for entry in in_list:
        if isinstance(entry, tuple) and check_value in range(*entry):
            return True
        elif check_value == entry:
            return True
    return False


def str_to_bool(str_bool: str) -> bool:
    """Simple helper to turn a string of true/false into Bool

    Args:
        str_bool: A boolean value as string

    Returns:
        Boolean True/False

    Raises:
        Raises ValueError if it cannot be converted bo boolean
    """
    if str_bool.lower() == "true":
        return True
    elif str_bool.lower() == "false":
        return False

    raise ValueError(f"{str_bool} could not be converted to bool")


class ThinkstConnectorManager(ThinkstManager):
    """
    The Connector specific implementation of the ThinkstManager
    """
    def __init__(
        self,
        api_key: str,
        console_hash: str,
        siemplify:  SiemplifyConnectorExecution,
        verify_ssl: bool = True,
    ) -> None:
        super().__init__(
            api_key=api_key,
            console_hash=console_hash,
            siemplify=siemplify,
            verify_ssl=verify_ssl)

        # The 'inflight_x' variants are used to keep track track of latest ID
        # and timestamp while alerts from the console has been processed. Once
        # that has been successfull if will be saved to the siemplify_context,
        # and kept track of with the 'completed_x' variants.
        self.inflight_id = 0
        self.inflight_timestamp = 0

        self.skip_info_prio = siemplify.extract_connector_param(
            param_name="Ignore Informative",
            default_value="false"
        )
        self.skip_info_prio = str_to_bool(self.skip_info_prio)

        # Make the context unique per-console
        self.context_id = f"{THINKST_CONTEXT_IDENTIFIER}.{console_hash}"

        self.completed_id = siemplify.get_connector_context_property(
            identifier=self.context_id,
            property_key=THINKST_UPDATE_KEY,
        )
        self.completed_timestamp = siemplify.get_connector_context_property(
            identifier=self.context_id,
            property_key=THINKST_LAST_TIMESTAMP,
        )

    def _fetch_console_alerts(self, page_limit: int = 20) -> list[dict]:
        """
        Fetch new alerts from the Canary Console

        This calls the api, handle pagination, and returns all the incidents
        since the last request. The 'last request' is handled by a few layers
        of fallback methods:
            - Try to use the last stored 'update_id' field
            - If that does not exist try to use the stored timestamp
            - And if that does not exist use a fixed time
              (THINKST_FALLBACK_TIME_MINS) in the past

        Args:
            page_limit: Paramter to tell the API to paginate the response

        Returns:
            All the incidents as json data
        """
        api_endpoint = f"{self.api_base_url}/incidents/unacknowledged"
        params = {"limit": str(page_limit)}

        # Prepare to grab incidents from a certain point in time. First try
        # from previous id, then try previous timestamp, and if that is not set
        # use THINKST_FALLBACK_TIME_MINS
        if self.completed_id:
            params["incidents_since"] = self.completed_id
        elif self.completed_timestamp:
            # The timestamp is stored as UNIX time in int, but the API expects
            # a string, convert it
            timestamp = datetime.fromtimestamp(
                self.completed_timestamp,
                timezone.utc
            ).strftime("%Y-%m-%d-%H:%M:%S")
            params["newer_than"] = timestamp
        else:
            params["newer_than"] = get_past_time(THINKST_FALLBACK_TIME_MINS)

        # Collect incidents accross different pages
        new_alerts = []
        last_page = False
        while not last_page:
            last_page = True
            incidents = self.api_get_request(api_endpoint, params=params)
            if cursor := incidents.get("cursor"):
                if cursor_next := cursor.get("next"):
                    params["cursor"] = cursor_next
                    # "limit" parameter is only valid for the first request
                    params.pop("limit", None)
                    last_page = False

            # Keep track of the maximum id and timestamp as we
            # iterate through the pages
            self.inflight_id = max(
                self.inflight_id,
                incidents.get("max_updated_id", 0)
            )
            self.inflight_timestamp = max(
                self.inflight_timestamp,
                incidents.get("updated_timestamp", 0)
            )

            for incident in incidents.get("incidents", []):
                new_alerts.append(incident)

        return new_alerts

    def _gen_portal_url(self, hash_id: str) -> str:
        return f"{self.console_url}/nest/incidents/{hash_id}"

    def _gen_hostname(self, hostname: str) -> Optional[str]:
        if hostname == "N/A":
            return None
        return str(hostname)

    def _gen_annotation(self, annotation: dict) -> Optional[str]:
        if annotation == {}:
            return None
        return json.dumps(annotation)

    def _get_priority(self, logtype: str) -> str:
        """
        Get priority for specific incident types

        This uses the 'value_in_ranged_list' helper to check if the 'logtype'
        is in a specific range of values. This can be used to configure what
        priority level should be assigned to every type of event. If the
        'logtype' is not in any of the list it will return the default
        priority of 'CRITICAL'.

        Some of the event lists might be empty, they are just placeholders
        to allow for easy addition of more priority mappings should it be
        needed.

        Args:
            logtype: The logtype which corresponds with the type of incident

        Returns:
            A string value of the relevant priority
        """
        # Informative = -1,Low = 40,Medium = 60,High = 80,Critical = 100.
        log_int = int(logtype)
        informative_events: Sequence[int | tuple[int, int]] = [
            1004,  # Canary Disconnected
            23002,  # Canary Settings Changed
            23001,  # Console Settings Changed
            23003,  # Flock Settings Changed
            ]
        low_events: Sequence[int | tuple[int, int]] = []
        medium_events: Sequence[int | tuple[int, int]] = [
            (5001, 5010),  # Port scan incident range 1
            (5011, 5013),  # Port scan incident range 2
        ]
        high_events: Sequence[int | tuple[int, int]] = []

        if value_in_ranged_list(informative_events, log_int):
            return str(PRIORITY_INFO)
        if value_in_ranged_list(low_events, log_int):
            return str(PRIORITY_LOW)
        if value_in_ranged_list(medium_events, log_int):
            return str(PRIORITY_MED)
        if value_in_ranged_list(high_events, log_int):
            return str(PRIORITY_HIGH)

        return str(PRIORITY_CRIT)

    def _gen_new_val(self, in_val: Any) -> Optional[str]:
        """
        Get the string representation of in_val for event mapping

        If the value is None, "", or -1, return None. Or if the str()
        conversion fails, just return None. This will cause this key/value
        combination to not be included in the event data.

        Args:
            in_val: The input value to convert

        Returns:
            str(in_val) or None
        """

        if in_val in [None, "", -1, "-1"]:
            return None

        try:
            return str(in_val)
        except Exception:
            self.logger.info(f"Converting {in_val} to string failed, skipping.")
            return None

    def _get_new_key_val(self, in_dict: dict) -> dict:
        """
        Converts existing dictionary key/values to new ones

        This function is used to convert an existing key/value pairs in the input
        dictionary into a new key, value pair. The 'common_mapping' dictionary
        is used for this. The original key is used to lookup a tuple in the
        mapping dictionary to find a new key, as well as a transformation function
        that needs to be applied to the value. The argument to the transformation
        function is always just the original value.

        Note: This returns a new dictionary, and if the key is not present in
        the mapping dictionary it will not be included in the result. The transformer
        function can also return 'None' as indicator that this key should be
        skipped.

        Args:
            in_dict: Original values to convert to new dict

        Returns:
            Dictionary containing transformed key/value pairs based on the
            'common_mapping' dictionary.
        """
        common_mapping: dict[str, tuple[str, Callable]] = {
            "summary": ("Name", self._gen_new_val),
            "logtype": ("Priority", self._get_priority),
            "memo": ("Reminder", self._gen_new_val),
            "name": ("DestinationHostName", self._gen_hostname),
            "flock_name": ("FlockName", self._gen_new_val),
            "flock_id": ("FlockId", self._gen_new_val),
            "id": ("AlertId", self._gen_new_val),
            "hash_id": ("PortalURL", self._gen_portal_url),
            "created": ("StartTime", to_unix_milliseconds),
            "updated_time": ("EndTime", to_unix_milliseconds),
            "src_port": ("SourcePort", self._gen_new_val),
            "src_host": ("SourceAddress", self._gen_new_val),
            "src_host_reverse": ("SourceHostName", self._gen_new_val),
            "dst_port": ("DestinationPort", self._gen_new_val),
            "dst_host": ("DestinationAddress", self._gen_new_val),
            "USERNAME": ("IncidentUserName", self._gen_new_val),
            "PASSWORD": ("IncidentPassword", self._gen_new_val),
            "KEY": ("IncidentSSHPubKey", self._gen_new_val),
            "matched_annotations": ("Annotations", self._gen_annotation),
            "FILENAME": ("FileName", self._gen_new_val),
            "USER": ("IncidentUserName", self._gen_new_val),
            "REMOTENAME": ("smb_RemoteName", self._gen_new_val),
            "DOMAIN": ("smb_Domain", self._gen_new_val),
            "SMBARCH": ("smb_Architecture", self._gen_new_val),
            "SHARENAME": ("smb_ShareName", self._gen_new_val),
            "MODE": ("smb_Mode", self._gen_new_val),
        }

        new_dict = {}
        for old_key, old_val in in_dict.items():
            new_key, func = common_mapping.get(old_key, (None, None))
            # If key is not present in mapping it is not included in the new dictionary
            if not new_key:
                continue
            if callable(func):
                # get the transformed new value calling the function from the tuple
                new_val = func(old_val)
                # The transformer function might return "None" as indication that
                # the key should not be included
                if new_val is None:
                    continue
            else:
                new_val = old_val
            new_dict[new_key] = new_val

        return new_dict

    def _gen_event_name(self, event: Optional[dict], incident: dict, alert_name: bool = False):
        """
        Generate an incident name

        The level of detail depens on whether or not this is being generated for an
        alert or an event inside the alert. The alert has limited display space,
        so this returns a slightly shorter name.

        Args:
            event: A single event dictionary. Might be 'None' in some cases
            incident: The incident dictionary
            alert_name: Set if it should generate an alert name instead of event name

        Returns:
            String of the new name
        """
        incident_desc = incident.get("description", {})
        desc = incident_desc.get("description", "")

        if "canarytoken" not in incident.get("id", "") or event is None:
            return f"{desc}"
        else:
            # Do token things
            token_type = event.get("type", "")
            token_name = TOKEN_NAME_MAP.get(token_type, token_type)
            if alert_name:
                return f"{token_name} {desc}"
            memo = incident_desc.get("memo", "")
            return f"{token_name} {desc}: {memo}"

    def _parse_events(self, events: list[dict], incident: dict) -> list[dict]:
        """
        Generate SOAR event entries from Canary Console Incidents

        The '_get_new_key_val' helper is used to create a list of new event
        dictionaries with keys and values understandable by the SOAR
        integration.

        Note: The 'events' list might be empty, in which case just the single
        'event_common' dictionary is returned as a list entry.

        Args:
            events: The list of events associated with the incident
            incident: The original incident

        Returns:
            A list of flat event dictionaries which is valid to add to
            AlertInfo().events
        """
        incident_desc = incident.get("description", {})
        event_common = self._get_new_key_val(incident)
        event_common.update(self._get_new_key_val(incident_desc))
        event_common["DeviceProduct"] = THINKST_PRODUCT
        event_common["device_product"] = THINKST_PRODUCT
        event_common["DeviceVendor"] = THINKST_VENDOR
        event_common["device_vendor"] = THINKST_VENDOR
        if "canarytoken" in incident.get("id", ""):
            event_common["SourceType"] = "Canarytoken"
        elif incident_desc.get("logtype", "") in THINKST_OPERATIONAL_LOGTYPES:
            event_common["SourceType"] = "Operational"
        else:
            event_common["SourceType"] = "Honeypot"

        # Some incidents do not generate an 'events' list, just return
        # the information common to all events.
        if events == []:
            event_common["Name"] = self._gen_event_name(None, incident)
            return [event_common]

        alert_events = []
        for event in events:
            # Every event contains the common event data + event specific data
            new_event = copy.deepcopy(event_common)
            new_event.update(self._get_new_key_val(event))
            # Event naming is more complicated than just a simple
            # transformation function, so populate it here instead
            new_event["Name"] = self._gen_event_name(event, incident)
            new_event["Event_RawJSON"] = json.dumps(event)
            new_event["Alert_RawJSON"] = json.dumps(incident)
            alert_events.append(new_event)
        return alert_events

    def _fill_alert_info(self, event: Optional[dict], incident: dict) -> AlertInfo:
        """
        Create and populate the AlertInfo object

        Note: This excludes the event information

        Args:
            event: Just a single event - used to generate the alert name
            incident: The Canary Console incident data

        Returns:
            The populated AlertInfo object
        """
        incident_desc = incident.get("description", {})

        alert_info = AlertInfo()
        alert_info.id = incident.get("id")
        alert_info.display_id = incident.get("id")
        alert_info.ticket_id = incident.get("id")
        alert_info.identifier = incident.get("id")

        name = self._gen_event_name(event, incident, alert_name=True)
        alert_info.name = name
        alert_info.rule_generator = name

        start_time = to_unix_milliseconds(incident_desc.get("created", 0))
        end_time = to_unix_milliseconds(incident.get("updated_time", 0))

        # Adjust for bug where this will show as 1970 if they are the same
        if end_time == start_time:
            end_time += 1
        alert_info.start_time = start_time
        alert_info.end_time = end_time

        log_type = incident_desc.get("logtype", "")
        alert_info.priority = int(self._get_priority(log_type))

        alert_info.device_vendor = THINKST_VENDOR
        alert_info.device_product = THINKST_PRODUCT
        alert_info.environment = self.siemplify.context.connector_info.environment

        return alert_info

    def fetch_alerts(self) -> list[AlertInfo]:
        """
        Fetches and converts Canary Console incidents into SOAR AlertInfo objects

        This fetches the latest incidents from the Canary console, use the helper
        functions to exctract and transform the data, and then returns it as a
        list of AlertInfo objects.

        Returns:
            A list of AlertInfo() objects which can be used by the SiemplifyConnector
        """
        alerts = []
        self.logger.debug("Fetching Canary Console alerts")
        incidents = self._fetch_console_alerts(page_limit=20)
        self.logger.debug("Canary Console Alerts fetched, converting to AlertInfo")
        for incident in incidents:
            description = incident.get("description", {})

            # If "Ignore Informative" is set by the user then do not create
            # an alert for this incident
            if self.skip_info_prio:
                logtype = description.get("logtype")
                if logtype and self._get_priority(logtype) == "-1":
                    continue

            # Fetch and parse the events from the Canary Console
            console_events = description.pop("events", [])
            alert_events = self._parse_events(console_events, incident)

            # Generate and fill in the basic AlertInfo object
            event0 = console_events[0] if len(console_events) > 0 else None
            alert_info = self._fill_alert_info(event0, incident)

            # Add the parsed events and entities to it, and add it to the list
            alert_info.events = alert_events
            alerts.append(alert_info)

        # Allerts have been collected succesfully, store the ID and timestamp
        self.siemplify.set_connector_context_property(
            identifier=self.context_id,
            property_key=THINKST_UPDATE_KEY,
            property_value=self.inflight_id,
        )
        self.siemplify.set_connector_context_property(
            identifier=self.context_id,
            property_key=THINKST_LAST_TIMESTAMP,
            property_value=self.inflight_timestamp,
        )
        return alerts
