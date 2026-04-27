# ============================================================================#
# title           :FireEyeHXManager.py
# description     :This Module contain all FireEye HX operations functionality
# author          :avital@siemplify.co
# date            :24-06-2018
# python_version  :2.7
# libreries       :requests
# requirments     :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #
from __future__ import annotations
import requests
import json

from .FireEyeHXParser import FireEyeHXParser
from .UtilsManager import get_earliest_event_at_datetime

# ============================== CONSTS ===================================== #
BASE_PATH = "{}/hx/api/{}"
HEADERS = {"Accept": "application/json", "Content-type": "application/json"}

STOPPED_STATE = "STOPPED"

LIMIT = 1000

SEARCH_LIMIT_HAS_BEEN_REACHED_STATUS_CODE = 409


# ============================= CLASSES ===================================== #
class FireEyeHXManagerError(Exception):
    """
    General Exception for FireEye HX manager
    """

    pass


class FireEyeHXNotFoundError(Exception):
    """
    Not Found Exception for FireEye HX manager
    """

    pass


class FireEyeHXManager:
    """
    FireEye HX Manager
    """

    def __init__(self, api_root, username, password, version="v3", verify_ssl=False):
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers = HEADERS
        self.session.auth = (username, password)
        self.api_root = BASE_PATH.format(
            api_root[:-1] if api_root.endswith("/") else api_root, version
        )
        self.session.headers["X-FeApi-Token"] = self.get_token()
        self.parser = FireEyeHXParser()
        self.loaded_hosts = {}

    def get_token(self):
        """
        Get a token (equals to login)
        """
        url = f"{self.api_root}/token"
        response = self.session.get(url)
        self.validate_response(response, "Unable to obtain token")
        token = response.headers.get("X-FeApi-Token")

        if not token:
            raise FireEyeHXManagerError(
                "Authentication failed. No X-FeApi-Token found."
            )

        return token

    def delete_token(self):
        """
        Delete a token (equals to logout)
        """
        old_session = self.session
        self.session = requests.Session()
        self.session.verify = old_session.verify
        self.session.headers = HEADERS
        self.session.headers["X-FeApi-Token"] = old_session.headers["X-FeApi-Token"]
        url = f"{self.api_root}/token"
        response = self.session.delete(url)

    def close_connection(self):
        """
        Close all active connection
        """
        self.delete_token()

    def get_hosts(
        self,
        limit=None,
        has_active_threats=None,
        has_alerts=None,
        agent_version=None,
        containment_queued=None,
        containment_state=None,
        host_name=None,
        os_platform=None,
        time_zone=None,
        query=None,
    ):
        """
        Get hosts
        :param limit: {int} The limit of hosts to search for
        :param has_active_threats: {bool} Whether the host has active threats
        :param has_alerts: {bool} Whether the host has alerts
        :param agent_version: {str} Filter by agent version
        :param containment_queued: {bool} Whether the host is queued for containment
        :param containment_state: {str} The containment state of the host.
            Possible values normal|contain|contain_fail|containing|contained|uncontain|uncontaining|wtfc|wtfu
        :param host_name: {str} Filter by host name
        :param os_platform: {str} Filter by family of operating systems. Valid values are win, osx, and linux.
        :param time_zone: {str} Filter by the timezone of the host
        :param query: {str} Searches all hosts connected to the specified Endpoint Security server.
            The search_term can be any hostname, IP address, or agent ID.
        :return: {list} List of found hosts
        """
        url = f"{self.api_root}/hosts"

        url_params = {
            "limit": limit or LIMIT,
            "offset": 0,
            "has_active_threats": has_active_threats,
            "has_alerts": has_alerts,
            "agent_version": agent_version,
            "containment_queued": containment_queued,
            "containment_state": containment_state,
            "hostname": host_name,
            "os.platform": os_platform,
            "time_zone": time_zone,
            "search": query,
        }

        # Remove None values
        url_params = {k: v for k, v in list(url_params.items()) if v is not None}

        if limit:
            # If limit is defined - return the found resutls
            response = self.session.get(url, params=url_params)
            self.validate_response(response, "Unable to get hosts")
            hosts = response.json().get("data", {}).get("entries", [])

        else:
            # Paginate the results and return all the found hosts
            hosts = self.paginate(url, url_params, "Unable to get hosts")

        return [self.parser.build_siemplify_host_obj(host) for host in hosts]

    def get_host_by_name(self, host_name):
        """
        Get host by name
        :param host_name: {str} The host name
        :return: {dict} The host
        """
        try:
            # Return the first host that matches the host name
            return self.get_hosts(host_name=host_name, limit=1)[0]
        except Exception:
            raise FireEyeHXNotFoundError(f"Host {host_name} was not found.")

    def get_hosts_by_ip(self, ip_address):
        """
        Get hosts by IP Address
        :param ip_address: {str} The IP address
        :return: {[host]} The matching hosts
        """
        hosts = self.get_hosts(query=ip_address)
        matching_hosts = []

        for host in hosts:
            if host.primary_ip_address == ip_address:
                matching_hosts.append(host)

        return matching_hosts

    def get_host_by_agent_id(self, agent_id):
        """
        Get host by agent id
        :param agent_id: {str} The agent id
        :return: {dict} The matching host
        """
        url = f"{self.api_root}/hosts/{agent_id}"
        response = self.session.get(url)
        self.validate_response(response, f"Host {agent_id} was not found.")
        return self.parser.build_siemplify_host_obj(response.json().get("data", {}))

    def get_all_agents_ids(self):
        """
        Get a list of all agents ids
        :return: {list} The agent ids
        """
        hosts = self.get_hosts()
        return [host._id for host in hosts]

    def get_agent_id(self, host_name):
        """
        Get agent id by host name
        :param host_name: {str} The host name
        :return: {str} The matching agent id
        """
        host = self.get_host_by_name(host_name)
        return host._id

    def contain_host_by_id(self, agent_id, approve=False):
        """
        Contain a host by id
        :param agent_id: {str} The agent id of the host to contain
        :param approve: {bool} Whether to approve containment or not
        :return: {bool} True if successful, exception otherwise.
        """
        url = f"{self.api_root}/hosts/{agent_id}/containment"

        if approve:
            payload = {"state": "contain"}

        else:
            payload = None

        response = self.session.post(url, json=payload)
        self.validate_response(response, f"Unable to contain host {agent_id}")
        return True

    def contain_host_by_name(self, host_name):
        """
        Contain a host by hostname
        :param host_name: {str} The hostname of the host to contain
        :return: {bool} True if successful, exception otherwise.
        """
        agent_id = self.get_agent_id(host_name)
        return self.contain_host_by_id(agent_id)

    def cancel_containment_by_id(self, agent_id):
        """
        Cancel containment by agent id
        :param agent_id: {str} The agent id of the host to un-contain
        :return: {bool} True if successful, exception otherwise
        """
        url = f"{self.api_root}/hosts/{agent_id}/containment"
        response = self.session.delete(url)
        self.validate_response(
            response, f"Unable to cancel containment for host {agent_id}"
        )
        return True

    def cancel_containment_by_name(self, host_name):
        """
        Cancel containment by hostname
        :param host_name: {str} The hostname of the host to un-contain
        :return: {bool} True if successful, exception otherwise
        """
        agent_id = self.get_agent_id(host_name)
        return self.cancel_containment_by_id(agent_id)

    def approve_containment_by_name(self, host_name):
        """
        Approve containment by hostname
        :param host_name: {str} The hostname of the host to approve its containment
        :return: {bool} True if successful, exception otherwise
        """
        agent_id = self.get_agent_id(host_name)
        return self.approve_containment_by_id(agent_id)

    def approve_containment_by_id(self, agent_id):
        """
        Approve containment by agent id
        :param agent_id: {str} The agent id of the host to approve its containment
        :return: {bool} True if successful, exception otherwise
        """
        url = f"{self.api_root}/hosts/{agent_id}/containment"
        response = self.session.patch(url, json={"state": "contain"})
        self.validate_response(
            response, f"Unable to approve containment for host {agent_id}"
        )
        return True

    def get_alerts(
        self,
        limit=None,
        has_share_mode=None,
        resolution=None,
        condition_id=None,
        agent_id=None,
        sort=None,
        min_id=None,
        alert_id=None,
        reported_at=None,
        source=None,
    ):
        """
        Get alerts
        :param limit: {int} The limit of alerts to search for
        :param has_share_mode: {str} Filter alerts that result from indicators with the specified
        share mode. Available values:
            - any: This value lists conditions belonging to indicators with any share mode. Exploit alerts are filtered out.
            - restricted: This value lists conditions that belong to restricted indicators.
            - unrestricted: This value lists conditions that belong to unrestricted indicators. This value is the default.
        :param resolution: {str} The resolution of the alert.
            Available values: active_threat, alert, block, partial_block.
        :param condition_id: {str} Filter by condition ID
        :param agent_id: {str} Filter by the agent ID
        :param sort: {str} What to sort by
        :param min_id: {str} Filter that returns only records with an _id field value great than the min_id value.
            than the minId value.
        :param alert_id: {str} Filter by alert ID.
        :param reported_at: {str} Filter by time when the server received the alert. ISO-8601 timestamp.
            Not dependent on alert type. In the Web UI (Hosts grid), this is shown as reported_at timestamp.
        :param source: {str} Source of alert - indicator of compromise. Valid values are:
            - "IOC" (indicator of compromise)
            - "EXD" (exploit detection)
            - "MAL" (malware alert)
            - dynamic source types such as RWARE, GEN, and so on.
        :return: {[Alert]}
        """
        url = f"{self.api_root}/alerts"
        url_params = {
            "has_share_mode": has_share_mode,
            "resolution": resolution,
            "agent._id": agent_id,
            "condition._id": condition_id,
            "min_id": min_id,
            "_id": alert_id,
            "source": source,
            "limit": limit or LIMIT,
            "offset": 0,
            "sort": sort,
        }

        if reported_at:
            url_params["filterQuery"] = json.dumps(
                {"operator": "gte", "arg": [reported_at], "field": "reported_at"}
            )

        # Remove None values
        url_params = {k: v for k, v in list(url_params.items()) if v is not None}

        if limit:
            # If limit was specified - return the found results
            response = self.session.get(url, params=url_params)
            self.validate_response(response, "Unable to get alerts")
            alerts = response.json().get("data", {}).get("entries", [])

        else:
            # Paginate through results and return all alerts
            alerts = self.paginate(url, url_params, "Unable to get alerts")

        if alerts:
            self.set_alerts_groups_ids(alerts)

        return [self.parser.build_siemplify_alert_obj(alert) for alert in alerts]

    def get_host_information(self, siemplify, host_id):
        """
        Get host information
        :param siemplify: {Siemplify} Siemplify object.
        :param host_id: {str} FireEye HX host id.
        :return: {dict} host information
        """
        host_data = self.read_host_info_from_loaded_data(host_id)

        if not host_data:
            siemplify.LOGGER.info(
                f"Host info for host {host_id} is not loaded. Sending request to load"
            )
            url = f"{self.api_root}/hosts/{host_id}"
            response = self.session.get(url)
            self.validate_response(response, "Unable to get host information")
            host_data = response.json().get("data", {})
            self.save_host_info(host_id, host_data)
        else:
            siemplify.LOGGER.info(f"Host info for host {host_id} already loaded.")

        return host_data

    def read_host_info_from_loaded_data(self, host_id):
        """
        Read host info from loaded data
        :param host_id: {str} The host id
        :return: {dict} Host info
        """
        return self.loaded_hosts.get(host_id, {})

    def save_host_info(self, host_id, host_data):
        """
        Save host info
        :param host_id: {str} The host id
        :param host_data: {dict} Host information
        """
        self.loaded_hosts[host_id] = host_data

    def get_alerts_for_connector(self, start_time, limit, alert_type):
        """
        Get alerts
        :param start_time: {str} Filter alerts that result from indicators with the specified
        :param limit: {int} A value Specified a number of alerts.
        :param alert_type: {str} FireEye HX alert types to ingest.
        :return: {[Alert]}
        """
        url = f"{self.api_root}/alerts"
        url_params = {
            "resolution": alert_type,
            "limit": limit or LIMIT,
            "offset": 0,
            "sort": "reported_at",
            "filterQuery": json.dumps(
                {"operator": "gt", "arg": [start_time], "field": "reported_at"}
            ),
        }

        response = self.session.get(url, params=url_params)
        self.validate_response(response, "Unable to get alerts")
        alerts = response.json().get("data", {}).get("entries", [])

        if alerts:
            self.set_alerts_groups_ids(alerts)

        return [self.parser.build_siemplify_alert_obj(alert) for alert in alerts]

    def set_alerts_groups_ids(self, alerts):
        """
        Set group ids to alerts
        :param alerts: The list of alerts
        """
        earliest_event_at = get_earliest_event_at_datetime(alerts)
        group_ids = self.get_alerts_groups_ids(earliest_event_at)
        ids_pairs = []

        for group_id in group_ids:
            ids_pairs.append((group_id, self.get_group_alerts_ids(group_id)))

        for alert in alerts:
            group_id = next(
                (
                    group_id
                    for group_id, alerts_ids in ids_pairs
                    if alert.get("_id") in alerts_ids
                ),
                "",
            )
            alert["group_id"] = group_id

    def get_alerts_groups_ids(self, earliest_event_time):
        """
        Get alert groups ids
        :param earliest_event_time: {str} The earliest event time to fetch data from
        :return: {list} The list of alert groups ids
        """
        url = f"{self.api_root}/alert_groups"
        params = {
            "filterQuery": json.dumps(
                {
                    "operator": "gte",
                    "arg": [earliest_event_time],
                    "field": "last_event_at",
                }
            )
        }

        response = self.session.get(url, params=params)
        self.validate_response(response, "Unable to get alert groups")
        alert_groups = response.json().get("data", {}).get("entries", [])
        return [alert_group.get("_id") for alert_group in alert_groups]

    def get_group_alerts_ids(self, group_id):
        """
        Get group alerts ids
        :param group_id: {str} The group id
        :return: {list} The list of alert ids
        """
        url = f"{self.api_root}/alert_groups/{group_id}/alerts"
        response = self.session.get(url)
        self.validate_response(response, f"Unable to get {group_id} group alerts")
        return [
            self.parser.build_siemplify_alert_obj(alert)._id
            for alert in response.json().get("data", {}).get("entries", [])
        ]

    def get_alert_by_id(self, alert_id):
        """
        Get alert by id
        :param alert_id: {str} The alert id
        :return: {dict} The alert info
        """
        url = f"{self.api_root}/alerts/{alert_id}"
        response = self.session.get(url)
        self.validate_response(response, f"Alert {alert_id} was not found")
        return self.parser.build_siemplify_alert_obj(response.json().get("data", {}))

    def logout(self):
        """
        Logout from FireEye HX
        :return: {bool} True if successful, exception otherwise
        """
        url = f"{self.api_root}/token"
        response = self.session.delete(url)
        self.validate_response(response, "Failed to logout with token")
        return True

    def suppress_alert(self, alert_id):
        """
        Suppress an alert
        :param alert_id: {str} The id of the alert to suppress
        :return: {bool} True if successful, exception otherwise.
        """
        url = f"{self.api_root}/alerts/{alert_id}"
        response = self.session.delete(url)
        self.validate_response(response, f"Unable to suppress alert {alert_id}")
        return True

    def get_indicator(self, category, name):
        """
        Get an indicator by category and name
        :param category: {str} The category name
        :param name: {str} The name of the indicator
        :return: {dict} The indicator info
        """
        url = f"{self.api_root}/indicators/{category}/{name}"
        response = self.session.get(url)
        self.validate_response(response, f"Unable to get indicator {category}-{name}")
        return self.parser.build_siemplify_indicator_obj(
            response.json().get("data", {})
        )

    def get_indicators(
        self,
        category=None,
        search=None,
        limit=None,
        share_mode=None,
        sort=None,
        created_by=None,
        alerted=None,
    ):
        """
        Get indicators
        :param category: {str} The indicator category
        :param search: {str} The searchTerm can be any name, category, signature, source, or
        condition value.
        :param limit: {int} The limit of indicators to search for
        :param share_mode: {str} Determines who can see the indicator.
            You must belong to the correct authorization group.
            Available values: any, restricted, unrestricted, visible.
        :param sort: {str} Sorts the results by the specified field in ascending order.
        :param created_by: {str} Person who created the indicator
        :param alerted: {bool} Whether the indicator resulted in alerts
        :return: {list} The found indicators
        """
        url = f"{self.api_root}/indicators"

        if category:
            url = f"{url}/{category}"

        url_params = {
            "search": search,
            "limit": limit or LIMIT,
            "offset": 0,
            "category.share_mode": share_mode,
            "sort": sort,
            "created_by": created_by,
            "stats.alerted_agents": alerted,
        }

        url_params = {k: v for k, v in list(url_params.items()) if v is not None}

        if limit:
            response = self.session.get(url, params=url_params)
            self.validate_response(response, "Unable to get indicators")
            indicators = response.json().get("data", {}).get("entries", [])

        else:
            indicators = self.paginate(url, url_params, "Unable to get indicators")

        return [
            self.parser.build_siemplify_indicator_obj(indicator)
            for indicator in indicators
        ]

    def get_indicator_conditions(
        self, category, name, limit=None, enabled=None, has_alerts=None
    ):
        """
        Get indicator's conditions
        :param category: {str} The indicator category
        :param name: {str} The indicator name
        :param limit: {int} The limit of indicators to search for
        :param enabled: {bool} Whether the condition is enabled or not
        :param has_alerts: {bool} Wheter the condition has raised alerts or not
        :return: {list} List of the indicator's conditions
        """
        url = f"{self.api_root}/indicators/{category}/{name}/conditions"
        url_params = {
            "limit": limit or LIMIT,
            "offset": 0,
            "enabled": enabled,
            "has_alerts": has_alerts,
        }

        url_params = {k: v for k, v in list(url_params.items()) if v is not None}

        if limit:
            # If limit is specified - return the found results
            response = self.session.get(url, params=url_params)
            self.validate_response(response, "Unable to get indicator conditions")
            return response.json().get("data", {}).get("entries", [])

        # Paginate through results and return the conditions
        return self.paginate(url, url_params, "Unable to get indicator conditions")

    def get_all_enabled_conditions(self, indicator_category, indicator_name):
        """
        Get the enabled conditions of an indicator
        :param indicator_category: {str} The indicator category
        :param indicator_name: {str} The indicator name
        :return: {list} List of the indicator's enabled conditions
        """
        return self.get_indicator_conditions(
            indicator_category, indicator_name, enabled=True
        )

    def search(self, query, host_set=None, hosts=None, exhaustive=False):
        """
        Search hosts
        :param query: {str} The search query
        :param host_set:
        :param hosts: {list} Hosts to search among
        :param exhaustive: {bool}
        :return: {dict} The created search info
        """
        url = f"{self.api_root}/searches"
        data = {"query": query, "exhaustive": exhaustive}

        if host_set:
            data["host_set"] = {"host_set._id": host_set}
        elif hosts:
            data["hosts"] = [{"_id": host} for host in hosts]

        response = self.session.post(url, json=data)

        self.validate_response(response, f"Unable to search {query}")
        return response.json().get("data", {})

    def get_search_information(self, search_id):
        """
        Get search information
        :param search_id: {str} The search id
        :return: {dict} The search info
        """
        url = f"{self.api_root}/searches/{search_id}"
        response = self.session.get(url)
        self.validate_response(
            response, f"Unable to get search {search_id} information"
        )
        return response.json().get("data", {})

    def is_search_completed(self, search_id):
        """
        Check whether a search is completed or not
        :param search_id: {str} The search id
        :return: {bool} True if completed, False otherwise.
        """
        search_info = self.get_search_information(search_id)

        # Get pending hosts
        pending = search_info.get("stats", {}).get("search_state", {}).get("PENDING", 0)

        # If search has stopped or no more pending hosts = search is complete
        return search_info.get("state") == STOPPED_STATE or pending == 0

    def get_search_results(self, search_id):
        """
        Get search results
        :param search_id: {str} The search id
        :return: {list} List of the results
        """
        url = f"{self.api_root}/searches/{search_id}/results"
        response = self.session.get(url)
        self.validate_response(response, f"Unable to get search {search_id} results")
        return response.json().get("entries", [])

    def stop_search(self, search_id):
        """
        Stop a search
        :param search_id: {str} The search id to stop
        :return: {bool} True if successful, exception otherwise.
        """
        url = f"{self.api_root}/searches/{search_id}/actions/stop"
        response = self.session.post(url)
        self.validate_response(response, f"Unable to stop search {search_id}")
        return True

    def delete_search(self, search_id):
        """
        Delete a search
        :param search_id: {str} The search id to delete
        :return: {bool} True if successful, exception otherwise.
        """
        url = f"{self.api_root}/searches/{search_id}"
        response = self.session.delete(url)
        self.validate_response(response, f"Unable to delete search {search_id}")
        return True

    def paginate(self, url, params, error_message):
        """
        Paginate through results and get all results
        :param url: {str} The url to target at
        :param params: {str} The request params
        :param error_message: {stt} The error message to display on failure
        :return: {list} The found results
        """
        response = self.session.get(url, params=params)
        self.validate_response(response, error_message)
        results = response.json().get("data", {}).get("entries", [])

        while response.json().get("data", {}).get("entries", []):
            params.update({"offset": len(results)})

            response = self.session.get(url, params=params)
            self.validate_response(response, error_message)
            results.extend(response.json().get("data", {}).get("entries", []))

        return results

    def get_file_acquisitions_for_host(
        self, agent_id, search_term=None, limit=None, filter_field=None
    ):
        """
        Get list of file acquisitions for a host.
        :param agent_id: host's agent id {string}
        :param search_term: {string} Searches all file acquisitions for hosts connected to the specified Endpoint Security server. The search_term can be any condition value.
        :param limit: {integer} Specifies how many records are returned. The limit_value must be an unsigned 32-bit integer. The default is 50.
        :param filter_field: Lists only results with the specified field value, results can be filtered by external correlation identifier (external_id).
        :return: list of entries {list}
        """
        url = f"{self.api_root}/hosts/{agent_id}/files"
        url_params = {
            "search": search_term,
            "offset": 0,
            "limit": limit or LIMIT,
            "filter_field": filter_field,
        }
        url_params = {k: v for k, v in list(url_params.items()) if v is not None}

        if limit:
            # If limit is specified - return the found results
            response = self.session.get(url, params=url_params)
            self.validate_response(response, "Error getting file acquisitions for host")
            acquisitions = response.json().get("data", {}).get("entries", [])

        else:
            # Paginate through results and return the conditions
            acquisitions = self.paginate(
                url, url_params, "Error getting file acquisitions for host"
            )

        return [
            self.parser.build_siemplify_file_acquisition_obj(acquisition)
            for acquisition in acquisitions
        ]

    def get_alerts_by_alert_group_id(self, alert_group_id, limit=None):
        """
        Function to get alerts by alert group ID
        :param alert_group_id {str}: Alert Group ID to fetch alerts from
        :param limit {int}: Limit of number of alerts to fetch
        :return: List Of GroupAlerts objects {list}
        """

        url = f"{self.api_root}/alert_groups/{alert_group_id}/alerts"
        url_params = {"offset": 0, "limit": limit or LIMIT}
        url_params = {k: v for k, v in list(url_params.items()) if v is not None}

        if limit:
            # If limit is specified - return the found results
            response = self.session.get(url, params=url_params)
            self.validate_response(
                response, f"Error getting alerts for given group id {alert_group_id}"
            )
            alerts = response.json().get("data", {}).get("entries", [])

        else:
            # Paginate through results and return the conditions
            alerts = self.paginate(
                url,
                url_params,
                f"Error getting alerts for given group id {alert_group_id}",
            )

        return [self.parser.build_siemplify_group_alert_obj(alert) for alert in alerts]

    def ackowledge_alert_groups(
        self, list_of_alert_ids, ack_comment, acknowledgement, limit=None
    ):
        """
        Function that acknowledges the alert group
        :param list_of_alert_ids {list}: List of Alert IDs
        :param ack_comment {int}: Acknowledgement Comment
        :param acknowledgement {bool}: True is we acknowledge False it not
        :param limit {bool}: Limit of results to return
        :return: Ack object {Ack}
        """

        url = f"{self.api_root}/alert_groups"
        payload = {
            "alert_ids": list_of_alert_ids,
            "acknowledgement": {"acknowledged": acknowledgement},
        }

        params = {}
        if limit:
            params["limit"] = limit

        if ack_comment:
            payload["acknowledgement"]["comment"] = ack_comment

        response = self.session.patch(url, json=payload, params=params)
        self.validate_response(
            response, "Error occured when trying to acknowledge alerts"
        )
        ack_response = response.json().get("data", {})

        return self.parser.build_siemplify_ack_obj(ack_response)

    def get_alert_group_details(self, alert_group_id):
        """
        Function to get details about an alert group
        :param alert_group_id {str}: Alert Group ID to fetch details about
        :return: GroupAlerts objects {GroupAlerts}
        """

        url = f"{self.api_root}/alert_groups/{alert_group_id}"

        response = self.session.get(url)
        self.validate_response(
            response, f"Error getting details for given group id {alert_group_id}"
        )
        alert_details = response.json().get("data", {})

        return self.parser.build_siemplify_group_obj(alert_details)

    def get_alert_groups(self, host_id, acknowledgement, limit):
        """
        Get alert groups
        :param host_id: {str} The host id.
        :param limit: {int} A number of alert groups to return.
        :param acknowledgement: {bool} Whether to return only acknowledged/unacknowledged.
        :return: {[Group]}
        """
        url = f"{self.api_root}/alert_groups"
        url_params = {
            "limit": limit or LIMIT,
            "offset": 0,
            "acknowledgement.acknowledged": acknowledgement,
            "host._id": host_id,
        }

        url_params = {k: v for k, v in list(url_params.items()) if v is not None}

        if limit:
            response = self.session.get(url, params=url_params)
            self.validate_response(response, "Unable to get alert groups")
            alert_groups = response.json().get("data", {}).get("entries", [])

        else:
            alert_groups = self.paginate(url, url_params, "Unable to get alert groups")

        return [self.parser.build_siemplify_group_obj(group) for group in alert_groups]

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate a response
        :param response: {requests.Response} The response
        :param error_msg: {unicode} The error message to display on failure
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            if response.status_code == SEARCH_LIMIT_HAS_BEEN_REACHED_STATUS_CODE:
                raise FireEyeHXManagerError("Search limit have been reached")

            try:
                error_messages = ", ".join(
                    [err.get("message") for err in response.json().get("details", [])]
                )

                if not error_messages:
                    error_messages = response.json()["message"]

                if response.status_code == 404:
                    raise FireEyeHXNotFoundError(f"{error_msg}: {error_messages}")

                raise FireEyeHXManagerError(f"{error_msg}: {error_messages}")

            except (FireEyeHXManagerError, FireEyeHXNotFoundError):
                raise

            except Exception:
                # Unable to parse JSON - return content of response
                raise FireEyeHXManagerError(f"{error_msg}: {error} {response.content}")
