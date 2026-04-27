from __future__ import annotations
from urllib.parse import urljoin
import requests
from .IvantiEndpointManagerParser import IvantiEndpointManagerParser
from .constants import ENDPOINTS, DELIVERY_METHOD_TYPES, FILTER_LOGIC
from .UtilsManager import validate_response, xml_to_json, filter_items
from requests_ntlm import HttpNtlmAuth
from soar_sdk.SiemplifyDataModel import EntityTypes


class IvantiEndpointManagerManager:
    def __init__(self, api_root, username, password, verify_ssl, siemplify_logger=None):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} Ivanti Endpoint Manager API root
        :param username: {str} Ivanti Endpoint Manager username
        :param password: {str} Ivanti Endpoint Manager password
        :param verify_ssl: {bool} Specifies if certificate that is configured on the api root should be validated
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.siemplify_logger = siemplify_logger
        self.parser = IvantiEndpointManagerParser()
        self.session = requests.session()
        self.session.verify = verify_ssl

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
        Test connectivity
        """
        url = self._get_full_url("ping")
        response = self.session.get(
            url, auth=HttpNtlmAuth(self.username, self.password)
        )
        validate_response(response)

    def get_queries(self, filter_logic, filter_value, limit):
        """
        Get queries
        :param filter_logic: {str} filter logic that should be applied
        :param filter_value: {str} filter value
        :param limit: {int} limit for results
        :return: {list} list of Query objects
        """
        url = self._get_full_url("list_queries")
        response = self.session.get(
            url, auth=HttpNtlmAuth(self.username, self.password)
        )
        validate_response(response)

        return filter_items(
            items=self.parser.build_query_objects(xml_to_json(response.content)),
            filter_key="name",
            filter_value=filter_value,
            filter_logic=filter_logic,
            limit=limit,
        )

    def get_delivery_methods(self, type, filter_logic, filter_value, limit):
        """
        Get delivery methods
        :param filter_logic: {str} filter logic that should be applied
        :param filter_value: {str} filter value
        :param limit: {int} limit for results
        :return: {list} list of DeliveryMethod objects
        """
        url = self._get_full_url(
            "list_delivery_method", type=DELIVERY_METHOD_TYPES.get(type)
        )
        response = self.session.get(
            url, auth=HttpNtlmAuth(self.username, self.password)
        )
        validate_response(response)

        return filter_items(
            items=self.parser.build_delivery_method_objects(
                xml_to_json(response.content)
            ),
            filter_key="name",
            filter_value=filter_value,
            filter_logic=filter_logic,
            limit=limit,
        )

    def get_column_set_fields(self, column_set, filter_logic, filter_value, limit):
        """
        Get column set fields
        :param column_set: {str} column set to get fields for
        :param filter_logic: {str} filter logic that should be applied
        :param filter_value: {str} filter value
        :param limit: {int} limit for results
        :return: {list} list of Field objects
        """
        url = self._get_full_url("list_column_set_fields", column_set=column_set)
        response = self.session.get(
            url, auth=HttpNtlmAuth(self.username, self.password)
        )
        validate_response(response)

        return filter_items(
            items=self.parser.build_field_objects(xml_to_json(response.content)),
            filter_key="name",
            filter_value=filter_value,
            filter_logic=filter_logic,
            limit=limit,
        )

    def get_machines(self, entities):
        """
        Get machines
        :param entities: {list} List of entities to filter with
        :return: {list} List of Machine objects
        """
        url = self._get_full_url("list_machines")
        filter_string = self._build_entities_filter(entities)
        response = self.session.get(
            url,
            auth=HttpNtlmAuth(self.username, self.password),
            params={"Filter": filter_string},
        )
        validate_response(response)

        return self.parser.build_machine_objects(xml_to_json(response.content))

    def get_machine_details(self, guid, column_set):
        """
        Get machine details
        :param guid: {str} The guid of machine
        :param column_set: {str} Column set to get machine details for
        :return:
        """
        url = self._get_full_url("get_machine_data")
        response = self.session.get(
            url,
            auth=HttpNtlmAuth(self.username, self.password),
            params={"GUID": guid, "ColumnDefXML": column_set},
        )
        validate_response(response)

        return self.parser.parse_machine_details(xml_to_json(response.content))

    def _build_entities_filter(self, entities):
        """
        Create filter string for request
        :param entities: {list} List of entities to create filter with
        :return: {str} Filter string
        """
        filters = []

        for entity in entities:
            if entity.entity_type == EntityTypes.ADDRESS:
                filters.append(
                    f'"Computer"."Network"."TCPIP"."Address" = "{entity.identifier}"'
                )
            elif entity.entity_type == EntityTypes.HOSTNAME:
                filters.append(f'"Computer"."Display Name" = "{entity.identifier}"')
            else:
                filters.append(
                    f'"Computer"."Network"."NIC Address" = "{entity.identifier}"'
                )

        return " OR ".join(filters)

    def get_vulnerabilities(self, guid, severities, limit):
        """
        List endpoint vulnerabilities
        :param guid: {str} endpoint guid
        :param severities: {list} list of severity filters
        :param limit: {int} limit for results
        :return: {list} list of Vulnerability objects
        """
        url = self._get_full_url("get_vulnerabilities", guid=guid)
        response = self.session.get(
            url, auth=HttpNtlmAuth(self.username, self.password)
        )
        validate_response(response)

        return filter_items(
            items=self.parser.build_vulnerability_objects(
                xml_to_json(response.content)
            ),
            filter_key="severity_code",
            filter_value=severities,
            filter_logic=FILTER_LOGIC.get("in_list"),
            limit=limit,
        )

    def get_packages(self, filter_logic, filter_value, limit):
        """
        Get packages
        :param filter_logic: {str} filter logic that should be applied
        :param filter_value: {str} filter value
        :param limit: {int} limit for results
        :return: {list} list of Package objects
        """
        url = self._get_full_url("list_packages")
        response = self.session.get(
            url, auth=HttpNtlmAuth(self.username, self.password)
        )
        validate_response(response)

        return filter_items(
            items=self.parser.build_package_objects(xml_to_json(response.content)),
            filter_key="name",
            filter_value=filter_value,
            filter_logic=filter_logic,
            limit=limit,
        )

    def get_column_sets(self, filter_logic, filter_value, limit):
        """
        Get column sets
        :param filter_logic: {str} filter logic that should be applied
        :param filter_value: {str} filter value
        :param limit: {int} limit for results
        :return: {list} list of ColumnSet objects
        """
        url = self._get_full_url("list_column_sets")
        response = self.session.get(
            url, auth=HttpNtlmAuth(self.username, self.password)
        )
        validate_response(response)

        return filter_items(
            items=self.parser.build_column_set_objects(xml_to_json(response.content)),
            filter_key="name",
            filter_value=filter_value,
            filter_logic=filter_logic,
            limit=limit,
        )

    def execute_query(self, query, limit):
        """
        Execute query
        :param query: {str} name of the query to execute
        :param limit: {int} limit for results
        :return: {list} list of QueryResult objects
        """
        url = self._get_full_url("execute_query", query_name=query)
        response = self.session.get(
            url, auth=HttpNtlmAuth(self.username, self.password)
        )
        validate_response(response)

        return filter_items(
            items=self.parser.build_query_result_objects(xml_to_json(response.content)),
            limit=limit,
        )

    def create_task(
        self, task_name, delivery_method, package_name, wakeup_machines, common_task
    ):
        """
        Create the task
        :param task_name: {str} The name of the task
        :param delivery_method: {str} The name of the delivery method
        :param package_name: {str} The name of the package
        :param wakeup_machines: {bool} If True, will wake up the machine during execution
        :param common_task: {bool} If True, will mark the task as common
        :return: {str} The id of the task
        """
        url = self._get_full_url("create_task")
        params = {
            "taskName": task_name,
            "deliveryMethodName": delivery_method,
            "packageName": package_name,
            "wakeupMachines": wakeup_machines,
            "commonTask": common_task,
            "async": "",
        }
        response = self.session.get(
            url, auth=HttpNtlmAuth(self.username, self.password), params=params
        )
        validate_response(response)

        return xml_to_json(response.content).get("ScheduledData", {}).get("TaskID")

    def add_device_to_task(self, task_id, device_name):
        """
        Add device to task
        :param task_id: {int} Id of the task
        :param device_name: {str} Device name
        :return: {bool} True, if successful, exception otherwise
        """
        url = self._get_full_url("add_device_to_task")
        params = {"taskId": task_id, "deviceName": device_name}
        response = self.session.get(
            url, auth=HttpNtlmAuth(self.username, self.password), params=params
        )
        validate_response(response)

    def start_task(self, task_id):
        """
        Initiate the task
        :param task_id: {int} Id of the task
        :return: {bool} True, if successful, exception otherwise
        """
        url = self._get_full_url("start_task")
        params = {"taskId": task_id, "rescheduleType": ""}
        response = self.session.get(
            url, auth=HttpNtlmAuth(self.username, self.password), params=params
        )
        validate_response(response)

    def get_task_result(self, task_id):
        """
        Fetch the task result
        :param task_id: {int} Id of the task
        :return: {TaskResult} TaskResult object
        """
        url = self._get_full_url("get_task_result")
        params = {"TaskID": task_id}
        response = self.session.get(
            url, auth=HttpNtlmAuth(self.username, self.password), params=params
        )
        validate_response(response)

        return self.parser.build_task_result_object(xml_to_json(response.content))

    def create_scan(self, scan_name, guids):
        """
        Create the scan
        :param scan_name: {str} The name of the scan
        :param guids: {str} List of entity guids to create filter with
        :return: {str} The id of the task
        """
        url = self._get_full_url("create_scan")
        filter_string = self._build_scan_entities_filter(guids)
        params = {"jobName": scan_name, "Filter": filter_string, "reserved": ""}
        response = self.session.get(
            url, auth=HttpNtlmAuth(self.username, self.password), params=params
        )
        validate_response(response)

        return xml_to_json(response.content).get("ScheduledData", {}).get("TaskID")

    def _build_scan_entities_filter(self, guids):
        """
        Create filter string for scan endpoints request
        :param guids: {list} List of entity guids to create filter with
        :return: {str} Filter string
        """
        return " OR ".join([f'"Computer"."Device ID" = {guid}' for guid in guids])
