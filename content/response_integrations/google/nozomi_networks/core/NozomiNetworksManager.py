from __future__ import annotations
from .NozomiNetworksParser import NozomiNetworksParser
from soar_sdk.SiemplifyDataModel import EntityTypes
import requests
import base64
import datetime
from urllib.parse import urljoin
from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time
from .UtilsManager import validate_response, filter_old_alerts

from .NozomiNetworksConstants import ENDPOINTS, HEADERS, CA_CERTIFICATE_FILE_PATH

from .NozomiNetworksExceptions import NozomiNetworksException


class NozomiNetworksManager:

    def __init__(
        self,
        api_root,
        username,
        password,
        ca_certificate_file,
        verify_ssl=False,
        siemplify_logger=None,
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: Nozomi API URL to connect to.
        :param username: Nozomi account username to use for connection.
        :param password: Nozomi account password to use for connection.
        :param ca_certificate_file: CA Certificate File - parsed into Base64 String.
        :param verify_ssl: Specify whether API URL certificate should be validated before connection.
        :param siemplify_logger: Siemplify logger.
        """
        self.api_root = api_root if api_root[-1:] == "/" else api_root + "/"
        self.username = username
        self.password = password
        self.siemplify_logger = siemplify_logger
        self.parser = NozomiNetworksParser()
        self.session = requests.session()
        self.session.headers = HEADERS
        self.session.auth = (self.username, self.password)

        if ca_certificate_file:
            try:
                file_content = base64.b64decode(ca_certificate_file)
                with open(CA_CERTIFICATE_FILE_PATH, "w+") as f:
                    f.write(file_content.decode("utf-8"))

            except Exception as e:
                raise NozomiNetworksException(e)

        if verify_ssl and ca_certificate_file:
            verify = CA_CERTIFICATE_FILE_PATH

        elif verify_ssl and not ca_certificate_file:
            verify = True
        else:
            verify = False

        self.session.verify = verify

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def test_connectivity(self):
        """
        Test connectivity to the Nozomi Networks.
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("test_connectivity")
        response = self.session.get(request_url)
        validate_response(response, "Unable to connect to Nozomi Networks.")

    def get_vulnerabilities(
        self,
        ip_addresses,
        cve_score,
        name_contains,
        cve_ids,
        record_limit,
        include_resolved,
    ):
        """
        Get vulnerabilities discovered by Nozomi device based on the query.
        :param ip_addresses: {list} List of ip addresses to filter with.
        :param cve_score: {int} Minimum CVE score to filter with.
        :param name_contains: {str} String that vulnerability name should contain.
        :param cve_ids: {list} List of CVE ids to filter with.
        :param record_limit: {int} Number of records to return.
        :param include_resolved: {bool} Whether to return resolved vulnerabilities.
        :return: {list} List of vulnerability objects.
        """
        query = self._build_search_query(
            ip_addresses=ip_addresses,
            cve_score=cve_score,
            name_contains=name_contains,
            cve_ids=cve_ids,
            record_limit=record_limit,
            include_resolved=include_resolved,
        )
        request_url = self._get_full_url("get_vulnerabilities", query=query)
        response = self.session.get(request_url)
        validate_response(response, "Unable to get vulnerabilities")
        return self.parser.build_all_objects(raw_json=response.json())

    def run_query(self, query, record_limit):
        """
        Run a query on Nozomi Networks device.
        :param query: {str} Query to execute
        :param record_limit: {int} Number of records to return.
        :return: {list} List of query results.
        """
        if record_limit:
            query = query.split("| head", 1)[0].strip() + f" | head {record_limit}"
        request_url = self._get_full_url("run_query", query=query)
        response = self.session.get(request_url)
        validate_response(response, "Unable to execute query")
        return self.parser.build_query_results(raw_json=response.json())

    def run_cli_command(self, cli_command):
        """
        Run a CLI command on Nozomi Networks device.
        :param cli_command: {str} CLI Command to execute
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("run_cli_command")
        payload = {"cmd": cli_command}
        self.session.headers.pop("Content-Type", None)
        response = self.session.post(request_url, data=payload)
        validate_response(response, "Unable to execute CLI command")

    def get_entity(self, identifier, entity_type):
        """
        Get entity info.
        :param identifier: {str} Entity identifier
        :param entity_type: {str} Entity type
        :return: {list}
        """
        query_type = "ip" if entity_type == EntityTypes.ADDRESS else "label"
        query = f" | where {query_type} == {identifier}"
        request_url = self._get_full_url("get_entity", query=query)
        response = self.session.get(request_url)
        validate_response(response, "Unable to get entity")
        nodes = self.parser.build_node_objects(raw_json=response.json())
        return sorted(nodes, key=lambda node: node.last_activity_time)

    def get_alerts(
        self,
        existing_ids,
        start_time,
        time_interval,
        lowest_severity,
        is_security,
        is_incident,
    ):
        """
        Fetch alerts.
        :param existing_ids: {list} The list of existing ids.
        :param start_time: {str} The datetime from where to fetch alerts.
        :param time_interval: {int} The time interval in minutes to fetch alerts.
        :param lowest_severity: {int} Lowest severity that will be used to fetch alerts.
        :param is_security: {bool} If true, will fetch security alerts.
        :param is_incident: {bool} If true, will fetch incident alerts.
        :return: {list} List of Alert objects.
        """
        query_string = self._build_query_string(
            [
                self._build_time_filter(start_time, time_interval),
                " | where ack == False",
                self._build_severity_filter(lowest_severity),
                self._build_security_filter(is_security, is_incident),
                " | where status == open",
            ]
        )
        request_url = self._get_full_url("get_alerts", query=query_string)
        response = self.session.get(request_url)
        validate_response(response, "Unable to get alerts")
        alerts = self.parser.build_all_alerts(raw_json=response.json())
        filtered_alerts = filter_old_alerts(
            logger=self.siemplify_logger, alerts=alerts, existing_ids=existing_ids
        )
        return sorted(filtered_alerts, key=lambda alert: alert.created_time)

    def _build_time_filter(self, start_time, time_interval):
        """
        Build time filter.
        :param start_time: {str} The starting datetime.
        :param time_interval: {int} The time interval in minutes.
        :return: {str} The query of time filter.
        """
        return (
            f" | where created_time > {convert_datetime_to_unix_time(start_time)} | where created_time < "
            f"{convert_datetime_to_unix_time(start_time  + datetime.timedelta(minutes=time_interval))}"
        )

    def _build_severity_filter(self, severity):
        """
        Build severity filter.
        :param severity: {int} Lowest severity that will be used to fetch alerts.
        :return: {str} The query of severity filter.
        """
        return f" | where severity >= {severity}" if severity else ""

    def _build_security_filter(self, is_security, is_incident):
        """
        Build security filter.
        :param is_security: {bool} If true, will fetch security alerts.
        :param is_incident: {bool} If true, will fetch incident alerts.
        :return: {str} The query of security filter.
        """
        return f" | where is_incident == {is_incident} | where is_security == {is_security}"

    def _build_query_string(self, queries):
        """
        Join filters.
        :param queries: {list} List of queries.
        :return: {str} Concatenated query
        """
        return "".join(queries)

    def _build_search_query(
        self,
        ip_addresses,
        cve_score,
        name_contains,
        cve_ids,
        record_limit,
        include_resolved,
    ):
        """
        Build search filter.
        :param ip_addresses: {list} List of ip addresses to filter with.
        :param cve_score: {int} Minimum CVE score to filter with.
        :param name_contains: {str} String that vulnerability name should contain.
        :param cve_ids: {list} List of CVE ids to filter with.
        :param record_limit: {int} Number of records to return.
        :param include_resolved: {bool} Whether to return resolved vulnerabilities.
        :return: {str} The query string.
        """
        addresses_query = (
            " | where {}".format(
                " OR ".join([f"node_id == {ip}" for ip in ip_addresses])
            )
            if ip_addresses
            else ""
        )
        score_query = f" | where cve_score >= {cve_score}" if cve_score else ""
        name_query = (
            f" | where cwe_name include? {name_contains}" if name_contains else ""
        )
        cve_ids_query = (
            " | where {}".format(" OR ".join([f"cve == {id}" for id in cve_ids]))
            if cve_ids
            else ""
        )
        resolved_query = f" | where resolved == {include_resolved}"
        limit_query = f" | head {record_limit}"

        return (
            addresses_query
            + score_query
            + name_query
            + cve_ids_query
            + resolved_query
            + limit_query
        )
