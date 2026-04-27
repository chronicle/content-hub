from __future__ import annotations
from urllib.parse import urljoin
import requests
from .constants import ENDPOINTS, GROUP_TYPES
from .UtilsManager import validate_response
from .F5BIGIPiControlAPIParser import F5BIGIPiControlAPIParser
from .F5BIGIPiControlAPIExceptions import (
    InvalidDataGroupException,
    InvalidInputException,
)


class F5BIGIPiControlAPIManager:
    def __init__(
        self, api_root, username, password, verify_ssl=False, siemplify_logger=None
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} API root of the F5 BIG-IP instance.
        :param username: {str} Username of the F5 BIG-IP account.
        :param password: {str} Password of the F5 BIG-IP account.
        :param verify_ssl: {bool} If enabled, verify the SSL certificate for the connection to the F5 BIG-IP server is valid.
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.username = username
        self.password = password
        self.logger = siemplify_logger
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.parser = F5BIGIPiControlAPIParser()
        self.session.auth = (self.username, self.password)

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
        request_url = self._get_full_url("ping")
        response = self.session.get(request_url)
        validate_response(response)

    def list_data_groups(self, paginate):
        """
        List data groups
        :param paginate: {bool} Indicates whether pagination should be applied
        :return: {list} List of Data Group objects
        """
        request_url = self._get_full_url("list_data_groups")

        if paginate:
            return self.parser.build_data_groups_list(
                self._paginate_results(
                    method="GET", url=request_url, err_msg="Unable to list data groups"
                )
            )

        response = self.session.get(request_url)
        validate_response(response, "Unable to list data groups")

        return self.parser.build_data_groups_list(response.json().get("items", []))

    def list_port_lists(self, paginate):
        """
        List port lists
        :param paginate: {bool} Indicates whether pagination should be applied
        :return: {list} List of Port List objects
        """
        request_url = self._get_full_url("list_port_lists")

        if paginate:
            return self.parser.build_port_lists_list(
                self._paginate_results(
                    method="GET", url=request_url, err_msg="Unable to list port lists"
                )
            )

        response = self.session.get(request_url)
        validate_response(response, "Unable to list port lists")

        return self.parser.build_port_lists_list(response.json().get("items", []))

    def list_address_lists(self, paginate):
        """
        List address lists
        :param paginate: {bool} Indicates whether pagination should be applied
        :return: {list} List of Address List objects
        """
        request_url = self._get_full_url("list_address_lists")

        if paginate:
            return self.parser.build_address_lists_list(
                self._paginate_results(
                    method="GET",
                    url=request_url,
                    err_msg="Unable to list address lists",
                )
            )

        response = self.session.get(request_url)
        validate_response(response, "Unable to list address lists")

        return self.parser.build_address_lists_list(response.json().get("items", []))

    def list_irules(self, paginate):
        """
        List iRules
        :param paginate: {bool} Indicates whether pagination should be applied
        :return: {list} List of iRule objects
        """
        request_url = self._get_full_url("list_irules")

        if paginate:
            return self.parser.build_irules_list(
                self._paginate_results(
                    method="GET", url=request_url, err_msg="Unable to list iRules"
                )
            )

        response = self.session.get(request_url)
        validate_response(response, "Unable to list iRules")

        return self.parser.build_irules_list(response.json().get("items", []))

    def get_address_list(self, address_list_name):
        """
        Get address list by name
        :param address_list_name: {str} The name of the address list
        :return: {AddressList} AddressList object
        """
        request_url = self._get_full_url("address_list", list_name=address_list_name)
        response = self.session.get(request_url)
        try:
            validate_response(response, "Unable to get address list")
        except InvalidInputException:
            raise InvalidDataGroupException(
                f"address list {address_list_name} was not found in F5 BIG-IP. "
                f"Please check the spelling."
            )

        return self.parser.build_address_list_object(response.json())

    def update_address_list(self, list_name, addresses):
        """
        Update address list
        :param list_name: {str} The name of the address list
        :param addresses: {list} List of addresses to update list with
        :return: {AddressList} AddressList object
        """
        request_url = self._get_full_url("address_list", list_name=list_name)
        payload = {"addresses": addresses}
        response = self.session.patch(request_url, json=payload)
        validate_response(response, "Unable to update address list")

        return self.parser.build_address_list_object(response.json())

    def get_data_group(self, group_name):
        """
        Get data group by name
        :param group_name: {str} The name of the group
        :return: {DataGroup} Data Group object
        """
        request_url = self._get_full_url("data_group", group_name=group_name)
        response = self.session.get(request_url)
        try:
            validate_response(response, "Unable to get data group")
        except InvalidInputException:
            raise InvalidDataGroupException(
                f"data group {group_name} was not found or doesn't have the IP type in "
                f"F5 BIG-IP. Please check the spelling."
            )

        return self.parser.build_data_group_object(response.json())

    def update_data_group(self, group_name, records):
        """
        Update data group
        :param group_name: {str} The name of the group
        :param records: {list} List of records to update group with
        :return: {DataGroup} Data Group object
        """
        request_url = self._get_full_url("data_group", group_name=group_name)
        payload = {"records": records}
        response = self.session.patch(request_url, json=payload)
        validate_response(response, "Unable to update data group")

        return self.parser.build_data_group_object(response.json())

    def get_port_list(self, port_list_name):
        """
        Get port list by name
        :param port_list_name: {str} The name of the port list
        :return: {PortList} Port List object
        """
        request_url = self._get_full_url("port_list", port_list_name=port_list_name)
        response = self.session.get(request_url)
        try:
            validate_response(response, "Unable to get port list")
        except Exception:
            raise InvalidDataGroupException(
                f"port list {port_list_name} was not found in F5 BIG-IP. "
                f"Please check the spelling."
            )

        return self.parser.build_port_list_object(response.json())

    def update_port_list(self, port_list_name, ports):
        """
        Update port list
        :param port_list_name: {str} The name of the port list
        :param ports: {list} List of ports to update list with
        :return: {PortList} Port List object
        """
        request_url = self._get_full_url("port_list", port_list_name=port_list_name)
        payload = {"ports": ports}
        response = self.session.patch(request_url, json=payload)
        validate_response(response, "Unable to update port list")

        return self.parser.build_port_list_object(response.json())

    def create_port_list(self, list_name, ports):
        """
        Create Port List
        :param list_name: {str} Name of the port list to be created
        :param ports: {str} Lists of ports that will be part of the new port list
        :return: {PortList} PortList object
        """
        request_url = self._get_full_url("create_port_list")
        ports_to_add = [{"name": port} for port in ports]
        payload = {"name": list_name, "ports": ports_to_add}
        response = self.session.post(request_url, json=payload)
        validate_response(response, "Unable to create a port list")

        return self.parser.build_port_list_object(response.json())

    def delete_port_list(self, list_name):
        """
        Delete Port List
        :param list_name: {str} Name of the port list to be deleted
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("port_list", port_list_name=list_name)
        response = self.session.delete(request_url)
        validate_response(response, "Unable to delete the port list")

    def create_data_group(self, group_name, group_type):
        """
        Create Data Group
        :param group_name: {str} Name of the group to be created
        :param group_type: {str} Type of the group to be created
        :return: {json} Raw response from the API with details about the data group
        """
        request_url = self._get_full_url("create_data_group")

        group_type = GROUP_TYPES.get(group_type)

        payload = {"name": group_name, "type": group_type}
        response = self.session.post(request_url, json=payload)
        validate_response(response, "Unable to greate a data group")

        return response.json()

    def delete_data_group(self, group_name):
        """
        Delete Data Group
        :param group_name: {str} Name of the group to be created
        """
        request_url = self._get_full_url("delete_data_group", group_name=group_name)

        response = self.session.delete(request_url)

        validate_response(response, "Unable to get port list")

    def create_address_list(self, list_name, addresses):
        """
        Create Address List
        :param list_name: {str} Name of the list to be created
        :param addresses: {list} IP addresses to add to the list
        :return: {AddressList} AddressList object
        """
        request_url = self._get_full_url("create_address_list")

        payload = {"name": list_name, "addresses": addresses}
        response = self.session.post(request_url, json=payload)
        validate_response(response, "Unable to create address list")

        return self.parser.build_address_list_object(response.json())

    def delete_address_list(self, list_name):
        """
        Delete Address List
        :param list_name: {str} Name of the group to be deleted
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("delete_address_list", list_name=list_name)
        response = self.session.delete(request_url)
        validate_response(response, "Unable to delete address list")

    def _paginate_results(
        self, method, url, params=None, body=None, err_msg="Unable to get results"
    ):
        """
        Paginate the results of a request
        :param method: {str} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {str} The url to send request to
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param err_msg: {str} The message to display on error
        :return: {list} List of results
        """
        if params is None:
            params = {}

        response = self.session.request(method, url, params=params, json=body)

        validate_response(response, err_msg)
        results = response.json().get("items", [])
        total_items = response.json().get("totalItems")
        res_count = len(results)

        while total_items and total_items > res_count:
            params.update({"$skip": res_count})

            response = self.session.request(method, url, params=params, json=body)
            validate_response(response, err_msg)
            results.extend(response.json().get("items", []))
            total_items = response.json().get("totalItems")
            res_count = len(results)

        return results

    def create_irule(self, name, rule):
        """
        Create iRule
        :param name: {str} Name of the iRule that needs to be created
        :param rule: {str} Rule that needs to be executed
        :return: {IRulesList} IRulesList object
        """
        request_url = self._get_full_url("create_irule")

        payload = {"name": name, "apiAnonymous": rule}

        response = self.session.post(request_url, json=payload)
        validate_response(response, "Unable to create an iRule")
        return self.parser.build_irule_object(response.json())

    def update_irule(self, name, rule):
        """
        Update iRule
        :param name: {str} Name of the iRule that needs to be updated
        :param rule: {str} Rule that needs to be executed
        :return: {IRulesList} IRulesList object
        """
        request_url = self._get_full_url("update_irule", name=name)

        payload = {"apiAnonymous": rule}

        response = self.session.patch(request_url, json=payload)
        validate_response(response, "Unable to update the iRule")
        return self.parser.build_irule_object(response.json())

    def delete_irule(self, name):
        """
        Delete iRule
        :param name: {str} Name of the iRule that needs to be deleted
        :return: {void}
        """
        request_url = self._get_full_url("delete_irule", name=name)
        response = self.session.delete(request_url)
        validate_response(response, "Unable to delete the iRule")
