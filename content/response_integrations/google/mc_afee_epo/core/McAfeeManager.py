from __future__ import annotations
import base64
from urllib.parse import urljoin

import requests
from requests import Session

from .McAfeeParser import McAfeeParser
from .McAfeeSession import APIError
from .McAfeeSession import Client
from .McafeeQueryBuilder import (
    Query,
    QueryBuilder,
    Condition,
    OperatorEnum,
    QueryOperatorEnum,
)
from .constants import PRODUCT_NAME, FILTER_STRATEGY_MAPPING
from .exceptions import (
    McAfeeEpoManagerException,
    McAfeeEpoCertificateException,
    McAfeeEpoInvalidGroupException,
    McAfeeEpoNotFoundException,
    McAfeeEpoBadRequestException,
    McAfeeEpoUnauthorizedException,
    McAfeeEpoPermissionException,
    McAfeeEpoTaskNotFoundException,
)
from .utils import LOGGER


SYSTEM_PROPERTIES_KEY_PREFIX = "EPOComputerProperties."
AGENT_PROPERTIES_KEY_PREFIX = "EPOLeafNode."

IP_FIELD_IN_SYSTEM_INFORMATION = "IPAddress"
HOST_FIELD_IN_SYSTEM_INFORMATION = "IPHostName"
NETBIOS_FIELD_IN_SYSTEM_INFORMATION = "ComputerName"
CA_CERTIFICATE_FILE_PATH = "cacert.pem"


API_ENDPOINTS = {
    "core_help": "core.help",
    "system_groups": "system.findGroups",
    "group_systems": "epogroup.findSystems",
    "system_apply_tag": "system.applyTag",
    "system_clear_tag": "system.clearTag",
    "system_info": "system.find",
    "core_execute_query": "core.executeQuery",
    "client_find_task": "clienttask.find",
    "client_run_task": "clienttask.run",
    "core_list_queries": "core.listQueries",
}


class McafeeEpoManager:
    def __init__(
        self,
        api_root,
        username,
        password,
        group_name=None,
        ca_certificate=None,
        verify_ssl=False,
        force_check_connectivity=False,
        logger=None,
    ):
        """
        The method is used to create session and set up connection.
        :param api_root {str}: the link to McAfee ePO REST API (Example: https://hostname:8443/remote)
        :param username {str}: user account at McAfee ePO.
        :param password {str}: password for mentioned above username at McAfee ePO
        :param group_name {str}: group name at McAfee ePO
        :param ca_certificate {str}: CA Certificate File - parsed into Base64 String
        :param verify_ssl {bool}: If enabled, verify the SSL certificate for the connection
        :param force_check_connectivity {bool}: test connectivity on init
        :param logger {SiemplifyLogger}:
        """
        self.api_root = self._get_adjusted_root_url(api_root)
        self.username = username
        self.password = password
        self.use_ssl = verify_ssl
        self.session = Session()
        self.session.verify = self._get_verify_value(ca_certificate, verify_ssl)
        self.client = Client(self.api_root, username, password, session=self.session)
        self.session.auth = (self.username, self.password)
        self.parser = McAfeeParser()
        self.logger = LOGGER(logger)
        self.group = None

        if force_check_connectivity:
            self.test_connectivity()

        if group_name:
            self.group = self.get_group_by_name(group_name=group_name)

    @staticmethod
    def _get_adjusted_root_url(api_root):
        return api_root if api_root[-1] == r"/" else f"{api_root}/"

    @staticmethod
    def _get_verify_value(ca_certificate, verify_ssl):
        """
        Get value for verify ssl
        :param ca_certificate: {str} CA Certificate File - parsed into Base64 String
        :param verify_ssl: {bool} Verify certificate or not
        :return: {str or bool} Certificate path or bool
        """
        if ca_certificate is not None and verify_ssl:
            try:
                file_content = base64.b64decode(ca_certificate)
                with open(CA_CERTIFICATE_FILE_PATH, "w") as f:
                    f.write(file_content.decode())
                    f.close()
                return CA_CERTIFICATE_FILE_PATH
            except Exception as e:
                raise McAfeeEpoCertificateException(f"Certificate Error: {e}")

        return verify_ssl

    @classmethod
    def get_api_error_message(cls, exception):
        """
        Get API error message
        :param exception: {Exception} The api error
        :return: {str} error message
        """
        try:
            return exception.response.json().get(
                "message"
            )  # @TODO check and fix message key
        except:
            return exception.response.content.decode()

    @classmethod
    def validate_response(cls, response, error_msg="An error occurred"):
        """
        Validate response
        :param response: {requests.Response} The response to validate
        :param error_msg: {str} Default message to display on error
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            error_message = cls.get_api_error_message(error) or error_msg

            if response.status_code == 401:
                raise McAfeeEpoUnauthorizedException(error_message)

            if response.status_code == 400:
                raise McAfeeEpoBadRequestException(error_message)

            if response.status_code == 403:
                raise McAfeeEpoPermissionException(error_message)

            if response.status_code == 404:
                raise McAfeeEpoNotFoundException(error_message)

            raise McAfeeEpoManagerException(f"{error_msg}: {error} {error_message}")

    @staticmethod
    def _get_url(url_id, **kwargs):
        """
        Get url from url identifier.
        :param url_id: {str} The id of url
        :param general_api: {bool} whether to use general api or not
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The url
        """
        return API_ENDPOINTS[url_id].format(**kwargs)

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param general_api: {bool} whether to use general api or not
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, self._get_url(url_id, **kwargs))

    def test_connectivity(self):
        """
        Test connectivity to McafeeEpo
        :return: {bool} True if successful, exception otherwise
        """
        try:
            response = self.session.get(self._get_full_url("core_help"))
            self.validate_response(response, error_msg="Authorization error")
            return True
        except Exception as e:
            raise McAfeeEpoManagerException(e)

    def get_group_by_name(self, group_name=None):
        """
        Get group id by name
        :param group_name: Group name
        return: {Group}
        """
        for group in self.parser.build_results(
            self.client(self._get_url("system_groups")), "build_group"
        ):
            if group_name.lower() == group.group_name.lower():
                return group

        raise McAfeeEpoInvalidGroupException(
            f"Group with given name {group_name} does not exist."
        )

    def get_systems(self, group_id):
        """
        Get Systems by group ID
        :param group_id: {int} ID of the group
        return: {SystemInformation}
        """
        params = {"groupId": group_id, "searchSubgroups": True}
        systems_json = self.client(self._get_url("group_systems"), params=params)
        systems = self.parser.build_results(systems_json, "build_system_information")

        if systems:
            return systems

        raise McAfeeEpoNotFoundException(
            f"No systems found with given group id {group_id}"
        )

    def apply_tag_to_endpoint_by_host_name(self, tag_name, host_name=None):
        """
        Apply tag name to an endpoint by host name.
        :param tag_name: {str}
        :param host_name: {str} endpoint's host address
        :return: {int} affected count
        """
        # We are using only 15 because of EPO truncation (15 symbols)
        host_name = host_name[:15]
        params = {"names": host_name, "tagName": tag_name}
        return self._apply_tag_to_endpoint(params=params)

    def apply_tag_to_endpoint_by_host_id(self, tag_name, host_id=None):
        """
        Apply tag name to an endpoint by host id.
        :param tag_name: {str}
        :param host_id: {str} ID of the host
        return: {int} affected count
        """
        params = {"ids": host_id, "tagName": tag_name}
        return self._apply_tag_to_endpoint(params=params)

    def clear_tag_from_endpoint_by_host_name(self, tag_name, host_name=None):
        """
        Clear tag name from an endpoint by host name.
        :param tag_name: {str}
        :param host_name: {str} endpoint's host address
        :return: {int} affected count
        """
        # We are using only 15 because of EPO truncation (15 symbols)
        host_name = host_name[:15]
        params = {"names": host_name, "tagName": tag_name}
        return self._clear_tag_from_endpoint(params=params)

    def clear_tag_from_endpoint_by_host_id(self, tag_name, host_id=None):
        """
        Clear tag name from endpoint by host id.
        :param tag_name: {str}
        :param host_id: {str} ID of the host
        return: {int} affected count
        """
        params = {"ids": host_id, "tagName": tag_name}
        return self._clear_tag_from_endpoint(params=params)

    def _apply_tag_to_endpoint(self, params):
        """
        Apply tag.
        :param params: {dict}
        return: {int} affected count
        """
        try:
            return self.client(self._get_url("system_apply_tag"), params=params)
        except APIError:
            raise McAfeeEpoNotFoundException(
                f'tag "{params.get("tagName")}" wasn\'t found in {PRODUCT_NAME}.'
            )

    def _clear_tag_from_endpoint(self, params):
        """
        Clear tag.
        :param params: {dict}
        return: {int} affected count
        """
        try:
            return self.client(self._get_url("system_clear_tag"), params=params)
        except APIError:
            raise McAfeeEpoNotFoundException(
                f'tag "{params.get("tagName")}" wasn\'t found in {PRODUCT_NAME}.'
            )

    def _get_matching_guid(self):
        return " ".join(
            f'"{machine_guid.agent_guid}"'
            for machine_guid in self.find_machines_guid(self.group.group_name)
        )

    def _get_machines_guid_where_condition(self, group_name):
        return f'(where (contains EPOBranchNode.NodeTextPath "{group_name}"))'

    def find_machines_guid(self, group_name):
        machines_guid = self._run_db_query(
            {
                "target": "EPOLeafNode",
                "select": f"{self._build_select_query(fields_to_join=['EPOLeafNode.AgentGUID'])}",
                "where": self._get_machines_guid_where_condition(group_name),
            }
        )

        if machines_guid:
            return self.parser.build_results(machines_guid, "build_machine_guid")

        raise McAfeeEpoManagerException(
            "No machines guid returned from db query running"
        )

    def _get_time_range_query(self, time_range):
        return (
            " (between EPOEvents.ReceivedUTC (timestamp {}) (timestamp {}))".format(
                *time_range
            )
            if time_range
            else ""
        )

    def _build_equal_query(self, fields_with_values):
        return " ".join(
            [
                f'(eq {field} "{value}")'
                for field, values in fields_with_values.items()
                for value in values
            ]
        )

    def _get_vse_where_condition(self, md5_hashes, time_range=None):
        find_hash_query = f"(where (and (or {self._build_equal_query({'VSECustomEvent.MD5': md5_hashes})})"

        if self.group:
            return (
                f"{find_hash_query} (in EPOEvents.AgentGUID {self._get_matching_guid()})"
                f"{self._get_time_range_query(time_range)})))"
            )
        else:
            return f"{find_hash_query}{self._get_time_range_query(time_range)}))"

    def _get_epe_where_condition(self, md5_hashes, time_range=None):
        find_hash_query = f"(where (and (or {self._build_equal_query({'EPExtendedEvent.TargetHash': md5_hashes})})"

        if self.group:
            return (
                f"{find_hash_query} (in EPOEvents.AgentGUID {self._get_matching_guid()})"
                f"{self._get_time_range_query(time_range)}))"
            )
        else:
            return f"{find_hash_query}{self._get_time_range_query(time_range)}))"

    def _get_sort_query(self, sort_order, sort_field):
        return f"(order ({sort_order.lower()} {sort_field} ) )"

    def _set_sort_query(self, params, sort_order=None, sort_field=None):
        if sort_order and sort_field:
            params["order"] = self._get_sort_query(
                sort_order=sort_order, sort_field=sort_field
            )

    def execute_custom_query(
        self,
        table_name,
        fields_to_return=None,
        where_condition=None,
        sort_field=None,
        sort_order=None,
        limit=None,
    ):
        """
        Execute a custom query
        :param table_name: {str} table from which will fetch results
        :param fields_to_return: {list} List of fields
        :param where_condition: {str} where clause for the query
        :param sort_field: {str} sort by 'field' key of data
        :param sort_order: {str} asc | desc
        :param limit: {int} events limit
        return: {list} List of CustomQuery objects
        """
        query_params = {"target": table_name, "where": where_condition}
        if fields_to_return:
            query_params["select"] = (
                f"{self._build_select_query(fields_to_join=fields_to_return, limit=limit)}"
            )

        self._set_sort_query(
            params=query_params, sort_order=sort_order, sort_field=sort_field
        )

        return self.parser.build_results(
            raw_json=self._run_db_query(query_params),
            method="build_custom_query",
            limit=limit,
        )

    def get_endpoint_events(
        self,
        *,
        table_name,
        ip_addresses=None,
        hostnames=None,
        mac_addresses=None,
        time_range=None,
        limit=None,
        sort_order=None,
        sort_field=None,
        fields_to_return=None,
    ):
        """
        Build and execute query conditions by provided keys and values.
        Reconstruct result after receiving
        :param table_name: {str}
        :param ip_addresses: {list}
        :param hostnames: {list}
        :param mac_addresses: {list}
        :param time_range: {tuple} start_unix_time, end_unix_time
        :param sort_field: {str}
        :param sort_order: {str} asc | desc
        :param fields_to_return: {str}
        :param limit: {int}
        return {list} List of EPEndpointEvent objects
        """
        query = QueryBuilder(
            [
                Query(
                    [
                        Condition(field="EPOEvents.TargetHostName", value=hostnames),
                        Condition(
                            field="EPOEvents.TargetIPV4",
                            value_formatter="ip_to_int",
                            value=ip_addresses,
                        ),
                        Condition(field="EPOEvents.TargetMAC", value=mac_addresses),
                    ]
                ),
                Query(
                    [
                        Condition(
                            field="between EPOEvents.ReceivedUTC",
                            value_formatter="set_time_range",
                            value=time_range,
                        )
                    ],
                    operator="",
                    use_parenthesis=False,
                ),
            ]
        )

        query_params = {"target": table_name, "where": str(query)}
        # with default fields for reconstructing data
        if fields_to_return:
            query_params["select"] = (
                f"{self._build_select_query(fields_to_join=fields_to_return, limit=limit)}"
            )

        self._set_sort_query(
            params=query_params, sort_field=sort_field, sort_order=sort_order
        )

        self.logger.info(
            f"------------ Query start ------------\n{query_params}"
            "\n------------- Query end -------------"
        )

        return self.parser.build_results(
            raw_json=self._run_db_query(query_params),
            method="build_endpoint_event",
            limit=limit,
        )

    def get_events_by_hash_with_vse_query(
        self, md5_hashes, sort_order=None, sort_field=None, time_range=None, limit=None
    ):
        """
        Get events by hash with vse query
        :param md5_hashes: {list} List of hashes
        :param sort_order: {str} asc | desc
        :param time_range: {tuple} start_unix_time, end_unix_time
        :param sort_field: {str} sort by 'field' key of data
        :param limit: {int} events limit
        return: {list} List of EPOEvent objects
        """
        # VSE SQL queries.
        query_params_vse = {
            "target": "EPOEvents",
            "joinTables": "VSECustomEvent",
            "where": self._get_vse_where_condition(
                md5_hashes=md5_hashes, time_range=time_range
            ),
        }

        self._set_sort_query(
            params=query_params_vse, sort_order=sort_order, sort_field=sort_field
        )

        return self.parser.build_results(
            raw_json=self._run_db_query(query_params_vse),
            method="build_epo_event",
            limit=limit,
        )

    def get_events_by_hash_with_epe_query(
        self, md5_hashes, sort_order=None, sort_field=None, time_range=None, limit=None
    ):
        """
        Get events by hash with epe query
        :param md5_hashes: {list} List of hashes
        :param sort_order: {str} asc | desc
        :param sort_field: {str} sort by 'field' key of data
        :param time_range: {tuple} start_unix_time, end_unix_time
        :param limit: {int} events limit
        return: {list} List of EPExtendedEvent objects
        """
        # EPO SQL queries.
        query_params_epe = {
            "target": "EPOEvents",
            "joinTables": "EPExtendedEvent",
            "where": self._get_epe_where_condition(
                md5_hashes=md5_hashes, time_range=time_range
            ),
        }

        self._set_sort_query(
            params=query_params_epe, sort_order=sort_order, sort_field=sort_field
        )

        return self.parser.build_results(
            raw_json=self._run_db_query(query_params_epe),
            method="build_epo_extended_event",
            limit=limit,
        )

    def get_system_info_or_raise(self, host_address):
        """
        Get system info ro raise
        :param host_address
        """
        system_info = self.get_system_info(host_address)

        if system_info:
            return system_info

        raise McAfeeEpoManagerException(
            f"System info for {host_address} was not found."
        )

    def get_system_info(self, host_address):
        """
        The method provides information about an endpoint. If McAfee ePO has a lot of endpoint instances with the
        same hostname, IP address, etc., the method provides only instance with the latest update date & time.
        :param host_address: IP address, hostname, MAC. It's recommended to use IP address as an input value
        because of there might be issues with non unique values.
        return: {SystemInformation}
        """
        params = {"searchText": host_address}
        systems_info_json = self.client(self._get_url("system_info"), params=params)
        results = [
            computer_info
            for computer_info in self.parser.build_results(
                systems_info_json, "build_system_information"
            )
            if host_address.lower()
            in [
                computer_info.ip_address,
                # For shortened entities (McAfee cuts hostnames to their netbios names, aka slices
                # after 15 characters and this is located in the ComputerName field
                computer_info.ip_host_name.lower(),
                # IPHostName contains the full fqdn of the machine
                # Try with only the hostname (without domain = split on first .)
                computer_info.ip_host_name.split(".")[0].lower(),
                # Try with full FQDN (including domain)
                computer_info.computer_name.lower(),
            ]
        ]
        if results:
            return sorted(results, key=lambda system_info: system_info.last_update)[-1]

    def get_system_info_safe(self, address):
        try:
            return self.get_system_info(address)
        except:
            pass

    def get_system_information(self, machine_location_id):
        """
        Get System information by machine location ID
        @param machine_location_id: Machine Location ID
        @return: Detailed System Information object
        """
        params = {
            "target": "EPOLeafNode",
            "select": self._build_select_query(
                self.get_system_information_select_fields()
            ),
            "where": self._get_system_info_where_condition(machine_location_id),
        }
        system_information = self._run_db_query(params=params)

        if not system_information:
            raise Exception("No system information returned from db query running")

        return self.parser.build_system_information(system_information[0])

    def get_systems_by_self_group(self):
        """
        Get systems by provided group
        return: {SystemInformation}: instance
        """
        if self.group:
            return self.get_systems(self.group.group_id)

    def _run_db_query(self, params):
        """
        The private method is to run query to the McAfee ePO database.
        Tables & Views may be found trough the following REST API call /remote/core.listTables.
        :param params: {str} params with SQL request.
        :return: {JSON}
        """
        return self.client(self._get_url("core_execute_query"), params=params)

    def run_query_by_id(self, query_id, result_limit=None):
        """
        :param query_id {str}
        :param result_limit {int}
        """
        return self.parser.build_results(
            raw_json=self._run_db_query({"queryId": query_id}),
            method="build_query_result",
            limit=result_limit,
        )

    def execute_entity_query(
        self,
        *,
        table_name,
        ip_addresses=None,
        hostnames=None,
        hashes=None,
        users=None,
        time_range=None,
        cross_entity_operator=None,
        ip_entity_key=None,
        hostname_entity_key=None,
        file_hash_entity_key=None,
        user_entity_key=None,
        urls=None,
        url_entity_key=None,
        limit=None,
        sort_order=None,
        email_address_entity_key=None,
        sort_field=None,
        emails=None,
        fields_to_return=None,
    ):
        """
        Build and execute query conditions by provided keys and values.
        Reconstruct result after receiving
        :param table_name: {str}
        :param ip_addresses: {list}
        :param hostnames: {list}
        :param ip_addresses: {list}
        :param hashes: {list}
        :param users: {list}
        :param urls: {list}
        :param emails {list}
        :param time_range: {tpl} (start time, end time) unix
        :param cross_entity_operator: {str} join query with or | and
        :param ip_entity_key: {str} query key name for ip_addresses
        :param hostname_entity_key: {str} query key name for ip_addresses
        :param file_hash_entity_key: {str} query key name for hashes
        :param user_entity_key: {str} query key name for users
        :param url_entity_key: {str} query key name for urls
        :param sort_field: {str}
        :param sort_order: {str} asc | desc
        :param email_address_entity_key: {str} query key name for users (check with regex match)
        :param fields_to_return: {str}
        :param limit: {int}
        return {list} List of EPEEntityEvent objects
        """
        cross_entity_operator = cross_entity_operator or QueryOperatorEnum.OR.value
        ip_addresses = [
            Condition(
                field=ip_entity_key, value_formatter="ip_to_int", value=ip_addresses
            )
        ]
        hostnames = [Condition(field=hostname_entity_key, value=hostnames)]
        hashes = [Condition(field=file_hash_entity_key, value=hashes)]
        emails = [Condition(field=email_address_entity_key, value=emails)]
        users = [Condition(field=user_entity_key, value=users)]
        urls = [Condition(field=url_entity_key, value=urls)]
        conditions = []

        if cross_entity_operator == QueryOperatorEnum.AND.value:
            conditions = [
                Query(ip_addresses),
                Query(hostnames),
                Query(hashes),
                Query(emails),
                Query(users),
                Query(urls),
            ]

        elif cross_entity_operator == QueryOperatorEnum.OR.value:
            conditions = [
                Query([*ip_addresses, *hostnames, *hashes, *emails, *users, *urls])
            ]

        query = QueryBuilder(
            [
                *conditions,
                Query(
                    [
                        Condition(
                            field="between EPOEvents.ReceivedUTC",
                            value_formatter="set_time_range",
                            value=time_range,
                        )
                    ],
                    operator="",
                    use_parenthesis=False,
                ),
            ]
        )

        query_params = {"target": table_name, "where": str(query)}

        if fields_to_return:
            query_params["select"] = (
                f"{self._build_select_query(fields_to_join=fields_to_return, limit=limit)}"
            )

        if query:
            self.logger.info(
                f"------------ Query start ------------\n{query_params}"
                "\n------------- Query end -------------"
            )

        self._set_sort_query(
            params=query_params, sort_field=sort_field, sort_order=sort_order
        )

        return self.parser.build_results(
            raw_json=self._run_db_query(query_params),
            method="build_epo_entity_event",
            limit=limit,
        )

    def _get_dat_version_where_condition(self, system_info):
        return f'(where (eq EPOProdPropsView_VIRUSCAN.LeafNodeID "{system_info.parent_id}"))'

    def get_threats(
        self,
        *,
        table_name,
        join_table,
        time_range,
        severity,
        systems_ids,
        fields_to_return=None,
        limit=None,
        unique_threats=False,
        analyzers_names=None,
        analyzers_names_as_blacklist=None,
    ):
        """
        The method provides all threats by given criteria
        :param table_name: table name
        :param time_range: time range to search incidents
        :param severity: severity values
        :param systems_ids:
        :param fields_to_return:
        :param limit:
        :param analyzers_names:
        :param analyzers_names_as_blacklist:
        :param unique_threats: include only unique jsons
        :return: {list} list of {Threat} model
        """
        analyzers_names_query_operator, analyzers_names_condition_operator = (
            (QueryOperatorEnum.AND.value, OperatorEnum.NE.value)
            if analyzers_names_as_blacklist
            else (QueryOperatorEnum.OR.value, OperatorEnum.EQ.value)
        )

        query = QueryBuilder(
            [
                Query(
                    [
                        Condition(
                            field="EPOEvents.ThreatSeverity",
                            value=severity,
                            operator=OperatorEnum.LE.value,
                            quotes=False,
                        )
                    ]
                ),
                Query([Condition(field="EPOEvents.AgentGUID", value=systems_ids)]),
                Query(
                    [
                        Condition(
                            field="EPOEvents.AnalyzerName",
                            value=analyzers_names,
                            operator=analyzers_names_condition_operator,
                        )
                    ],
                    operator=analyzers_names_query_operator,
                ),
                Query(
                    [
                        Condition(
                            field="between EPOEvents.ReceivedUTC",
                            value_formatter="set_time_range",
                            value=time_range,
                        )
                    ],
                    operator="",
                    use_parenthesis=False,
                ),
            ],
            operator=QueryOperatorEnum.AND.value,
        )

        query_params = {
            "target": table_name,
            "where": str(query),
            "joinTables": join_table,
            "select": f"{self._build_select_query(fields_to_join=fields_to_return, limit=limit)}",
        }
        self._set_sort_query(
            params=query_params, sort_order="asc", sort_field="EPOEvents.ReceivedUTC"
        )

        self.logger.info(
            f"------------ Query start ------------\n{query_params}"
            "\n------------- Query end -------------"
        )

        threats = self.parser.build_results(
            raw_json=self._run_db_query(query_params), method="build_threat"
        )

        if unique_threats:
            seen = set()
            return [
                threat
                for threat in threats
                if not (threat.hash_id in seen or seen.add(threat.hash_id))
            ]

        return threats[:limit]

    def get_dat_version(self, param):
        """
        The method provides DAT Version installed at the endpoint.
        :param param: IP address
        :return: {DatVersion}
        """

        system_info = self.get_system_info(param)

        if not system_info:
            raise McAfeeEpoManagerException("Error getting System Information.")

        params = {
            "target": "EPOProdPropsView_VIRUSCAN",
            "select": self._build_select_query(["EPOProdPropsView_VIRUSCAN.datver"]),
            "where": self._get_dat_version_where_condition(system_info),
        }

        dat_version = self._run_db_query(params=params)

        if dat_version:
            return self.parser.build_dat_version(dat_version[0])

        raise McAfeeEpoManagerException("Error getting DAT Version.")

    def _run_client_task(self, params):
        """
        The auxiliary method is use to run client task command.
        :params {dict} params for running task
        return: {Task}
        """
        return self.parser.build_task_status(
            self.client(self._get_url("client_run_task"), params=params)
        )

    def get_list_queries(self, limit=None):
        return self.parser.build_results(
            raw_json=self.client(self._get_url("core_list_queries")),
            method="build_query",
            limit=limit,
        )

    def get_list_queries_by_filter(self, value, filter_strategy, limit=None):
        """
        Get list queries by provided filter field and value
        :param value {str} value to compare
        :param filter_strategy {str} value to search
        :param limit {int}
        """
        queries = self.get_list_queries()

        if not (filter_strategy and value):
            return queries[:limit]

        return self.filter_queries(queries, filter_strategy, value, limit=limit)

    def filter_queries(self, queries, filter_strategy, value, limit=None):
        """
        Filter queries by provided filter field and value
        :param queries {list} List of Query objects
        :param value {str} value to compare
        :param filter_strategy {str} value to search
        :param limit {int}
        return {list} List of filtered queries
        """
        found_results = []

        for query in queries:
            if FILTER_STRATEGY_MAPPING[filter_strategy](query.name, value):
                found_results.append(query)

            if len(found_results) >= limit:
                break

        return found_results

    def get_client_tasks(self, search_text, limit=None):
        """
        Get client tasks by search text
        :param search_text: {str} The task text to include.
        :param limit: {int}
        return: {list} List of Task objects
        """
        return self.parser.build_results(
            raw_json=self.client(
                self._get_url("client_find_task"), params={"searchText": search_text}
            ),
            method="build_task",
            limit=limit,
        )

    def run_full_scan_by_system_name(self, client_task, system_name):
        """
        Run task to scan the endpoint by systems name.
        Pay attention the task you choose should have Virus Scan and On Demand Scan properties.
        Options should be set up at McAfee ePO.
        :param client_task: {Task}
        :param system_name: {str}
        return: {str} Text message if the task `s successfully.
        """
        return self._run_client_task(
            {
                "names": system_name[
                    :15
                ],  # We are using only 15 because of EPO truncation (15 symbols)
                "taskId": client_task.object_id,
                "productId": client_task.product_id,
            }
        )

    def run_full_scan_by_system_id(self, client_task, system_id):
        """
        Run task to scan the endpoint by system id.
        Pay attention the task you choose should have Virus Scan and On Demand Scan properties.
        Options should be set up at McAfee ePO.
        :param client_task: {Task}
        :param system_id: {int}
        return: {str} Text message if the task `s successfully.
        """
        return self._run_client_task(
            {
                "ids": system_id,
                "taskId": client_task.object_id,
                "productId": client_task.product_id,
            }
        )

    def get_virus_scan_agent_version(self, param):
        """
        The method provides Virus Scan Agent Version installed at the endpoint.
        :param param: IP address
        :return: Virus Scan Agent Version or null
        """

        system_info = self.get_system_info(param)

        if not system_info:
            raise Exception("Error getting System Information.")

        params = {
            "target": "EPOProdPropsView_VIRUSCAN",
            "select": self._build_select_query(
                ["EPOProdPropsView_VIRUSCAN.productversion"]
            ),
            "where": self._get_vsav_where_condition(system_info),
        }

        result = self._run_db_query(params=params)

        if result:
            return self.parser.build_vsav(result[0])

        raise Exception("Error getting last communication time.")

    def _get_vsav_where_condition(self, system_info):
        return f'(where (eq EPOProdPropsView_VIRUSCAN.LeafNodeID "{system_info.parent_id}"))'

    def get_task_by_name_or_raise(self, task_name):
        """
        The method returns task by provided Task Name or raise an exception
        :param task_name: the task name which you're going to use update agent at the endpoint.
        :return: {Task} instance if exists
        """
        result = self.get_client_tasks(search_text=task_name)

        if result:
            return result[0]

        raise McAfeeEpoTaskNotFoundException(
            f'Task "{task_name}" wasn\'t found in McAfee ePO. Please check the spelling.'
        )

    def update_mcafee_agent(self, entity, task):
        """
        The method returns task status
        :param entity: Entity identifier Hostname or IP address
        :param task: {Task} instance
        :return: {str} if response exists Exception otherwise
        """
        params = {
            "productId": task.product_id,
            "taskId": task.object_id,
            "names": entity[
                :15
            ],  # We are using only 15 because of EPO truncation (15 symbols)
        }
        result = self.client(self._get_url("client_run_task"), params=params)
        return self.parser.build_task_status(result)

    def _get_server_dat_where_conditin(self):
        return '(where (eq EPOMasterCatalog.ProductName "DAT"))'

    def get_server_dat(self):
        """
        The method is used to provide Master Repository Status Information (DAT only).
        :return: {ServerDat}
        """

        params = {
            "target": "EPOMasterCatalog",
            "select": self._build_select_query(["EPOMasterCatalog.ProductVersion"]),
            "where": self._get_server_dat_where_conditin(),
        }

        server_dat = self._run_db_query(params=params)

        if server_dat:
            return self.parser.build_server_dat(server_dat[0])

        raise McAfeeEpoManagerException("Error getting Server DAT.")

    def _get_last_comm_time_where_condition(self, system_info):
        return f'(where (eq EPOLeafNode.AutoID "{system_info.parent_id}"))'

    def get_last_comm_time(self, host_address):
        system_info = self.get_system_info(host_address)

        if not system_info:
            raise Exception("Error getting System Information.")

        params = {
            "target": "EPOLeafNode",
            "select": self._build_select_query(["EPOLeafNode.LastUpdate"]),
            "where": self._get_last_comm_time_where_condition(system_info),
        }

        result = self._run_db_query(params=params)

        if result:
            return self.parser.build_last_communication_time(result[0])

        raise Exception("Error getting last communication time.")

    @staticmethod
    def _build_select_query(fields_to_join, join_with=" ", limit=None):
        """
        Build select query
        :param fields_to_join: {list} List of conditions.
        :param join_with: {str} to join conditions
        :param limit: {int} using 'top' query
        :return: {str}
        """
        return f"(select {f'(top {limit}) ' if limit and fields_to_join else ''}{join_with.join(fields_to_join)} )"

    def _get_host_ips_status_where_condition(self, system_info):
        return f'(where (eq HIP8_Properties.ParentID "{system_info.parent_id}"))'

    def _get_system_info_where_condition(self, parent_id):
        """
        Build where condition of query
        :param parent_id: {int} Parent ID.
        :return: {str}
        """
        return f'(where (contains EPOComputerProperties.ParentID "{parent_id}"))'

    def get_host_ips_status(self, host_address):
        """
        :param host_address: {str}
        :return {HipProperty} instance:
        """
        system_info = self.get_system_info(host_address)
        if not system_info:
            raise McAfeeEpoManagerException("Error getting System Information.")

        params = {
            "target": "HIP8_Properties",
            "select": self._build_select_query(["HIP8_Properties.HIPSStatus"]),
            "where": self._get_host_ips_status_where_condition(system_info),
        }

        result = self._run_db_query(params=params)

        if result:
            return self.parser.build_hip_property(result[0])

        raise McAfeeEpoManagerException("Error getting Status.")

    def _get_host_nips_status_where_condition(self, system_info):
        return f'(where (eq HIP8_Properties.ParentID "{system_info.parent_id}"))'

    def get_host_nips_status(self, host_address):
        """
        :param host_address: {str}
        :return {HipProperty} instance:
        """
        system_info = self.get_system_info(host_address)
        if not system_info:
            raise McAfeeEpoManagerException("Error getting System Information.")

        params = {
            "target": "HIP8_Properties",
            "select": self._build_select_query(["HIP8_Properties.HIPSStatus"]),
            "where": self._get_host_nips_status_where_condition(system_info),
        }

        result = self._run_db_query(params=params)

        if result:
            return self.parser.build_hip_property(result[0])

        raise McAfeeEpoManagerException("Error getting Status.")

    def get_endpoint_system_info(self, host_address):
        """
        :param host_address: {str} Host Address
        :return: {SystemInformation} if exists by address name else raise an exception
        """
        # Get system info.
        system_info = self.get_system_info(host_address)

        if not system_info:
            raise Exception("System info does not exist")

        return system_info

    def get_system_information_select_fields(self):
        """
        Return all keys that should be selected from API for system information
        :return: {list} all fields for select
        """
        return [
            "EPOComputerProperties.TimeZone",
            "EPOComputerProperties.DefaultLangID",
            "EPOComputerProperties.UserName",
            "EPOComputerProperties.DomainName",
            "EPOComputerProperties.IPHostName",
            "EPOComputerProperties.IPV6",
            "EPOComputerProperties.IPAddress",
            "EPOComputerProperties.IPSubnet",
            "EPOComputerProperties.IPSubnetMask",
            "EPOComputerProperties.IPV4x",
            "EPOComputerProperties.IPXAddress",
            "EPOComputerProperties.SubnetAddress",
            "EPOComputerProperties.SubnetMask",
            "EPOComputerProperties.NetAddress",
            "EPOComputerProperties.OSType",
            "EPOComputerProperties.OSVersion",
            "EPOComputerProperties.OSCsdVersion",
            "EPOComputerProperties.OSBuildNum",
            "EPOComputerProperties.OSPlatform",
            "EPOComputerProperties.OSOEMID",
            "EPOComputerProperties.CPUType",
            "EPOComputerProperties.CPUSpeed",
            "EPOComputerProperties.ManagementType",
            "EPOComputerProperties.NumOfCPU",
            "EPOComputerProperties.CPUSerialNumber",
            "EPOComputerProperties.TotalPhysicalMemory",
            "EPOComputerProperties.FreeMemory",
            "EPOComputerProperties.FreeDiskSpace",
            "EPOComputerProperties.TotalDiskSpace",
            "EPOComputerProperties.IsPortable",
            "EPOComputerProperties.OSBitMode",
            "EPOComputerProperties.LastAgentHandler",
            "EPOComputerProperties.UserProperty1",
            "EPOComputerProperties.UserProperty2",
            "EPOComputerProperties.UserProperty3",
            "EPOComputerProperties.UserProperty4",
            "EPOComputerProperties.UserProperty5",
            "EPOComputerProperties.UserProperty6",
            "EPOComputerProperties.UserProperty7",
            "EPOComputerProperties.UserProperty8",
            "EPOComputerProperties.Free_Space_of_Drive_C",
            "EPOComputerProperties.Total_Space_of_Drive_C",
            "EPOComputerProperties.Vdi",
            "EPOComputerProperties.EmailAddress",
            "EPOComputerProperties.LastUpdate",
            "EPOComputerProperties.PlatformID",
            "EPOComputerProperties.SMBiosUUID",
            "EPOComputerProperties.SystemSerialNumber",
            "EPOComputerProperties.SystemRebootPending",
            "EPOComputerProperties.SystemModel",
            "EPOComputerProperties.SystemManufacturer",
            "EPOComputerProperties.SystemBootTime",
            "EPOComputerProperties.NumOfHardDrives",
            "EPOComputerProperties.EthernetMacAddressCount",
            "EPOComputerProperties.WirelessMacAddressCount",
            "EPOComputerProperties.OtherMacAddressCount",
            "EPOLeafNode.AgentGUID",
            "EPOLeafNode.LastUpdate",
            "EPOLeafNode.NodeName",
            "EPOComputerProperties.Description",
            "EPOLeafNode.Tags",
            "EPOBranchNode.NodeTextPath2",
        ]
