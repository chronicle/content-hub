from __future__ import annotations
from typing import Any

import copy
import urllib.parse

import requests

from .constants import (
    CREATE_PORT_OBJECT_URL,
    CREATE_PORT_OBJECT_PAYLOAD,
    GET_ALL_PORT_GROUP_OBJECTS_URL,
    GET_NETWORK_GROUP_OBJECT_BY_ID_URL,
    GET_NETWORK_GROUP_OBJECTS_URL,
    GET_PORT_GROUP_OBJECT_URL,
    GET_PORT_OBJECT_BY_ID_URL,
    GET_POLICIES_URL,
    GET_RULES_FOR_POLICY_URL,
    GET_RULE_URL,
    GET_URL_GROUPS_URL,
    GET_URL_GROUP_OBJECT_URL,
    IP_ADDRESS_LITERAL_PATTERN,
    OBTAIN_TOKEN_URL,
    PAGINATION_LIMIT,
    PAGE_SIZE,
    PORT_OBJECT_STRUCTURE,
    RULE_LITERAL_OBJECT,
    RULE_URL_PATTERN,
    UPDATE_URL_GROUP_PAYLOAD,
    UPDATE_PORT_GROUP_PAYLOAD,
)
from .exceptions import CiscoFirepowerManagerError


class CiscoFirepowerManager:
    def __init__(self, api_root, username, password, verify_ssl=False):
        self.api_root = self.validate_api_root(api_root)
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.auth = (username, password)

        # Update session headers and get domain uuid.
        self.domain_uuid = self.get_domain_uuid_and_update_headers()

    @staticmethod
    def validate_response(http_response):
        """
        Validate HTTP response.
        :param http_response: {HTTP response}
        :return: void
        """
        try:
            http_response.raise_for_status()
        except requests.HTTPError as err:
            raise CiscoFirepowerManagerError(
                f'HTTP error occurred, status code:"{http_response.status_code}", content:"{http_response.content}", ERROR: {err}'
            )

    @staticmethod
    def validate_api_root(api_root):
        """
        Validate API root string contains '/' at the end because 'urlparse' lib is used.
        :param api_root: api root url {string}
        :return: valid api root {string}
        """
        if api_root[-1] == "/":
            return api_root
        return api_root + "/"

    def get_domain_uuid_and_update_headers(self):
        """
        Update session headers and return domain uuid.
        :return: domain uuid {string}
        """
        request_url = urllib.parse.urljoin(self.api_root, OBTAIN_TOKEN_URL)
        response = self.session.post(request_url)
        self.validate_response(response)

        # Update headers.
        self.session.headers["X-auth-access-token"] = response.headers[
            "X-auth-access-token"
        ]
        self.session.headers["X-auth-refresh-token"] = response.headers[
            "X-auth-refresh-token"
        ]

        # Return domain uuid
        return response.headers.get("DOMAIN_UUID")

    def get_policy_id_by_name(self, policy_name):
        """
        Get policy id by it's name.
        :param policy_name: policy name {string}
        :return: policy id {string}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, GET_POLICIES_URL.format(self.domain_uuid)
        )
        response = self._paginated_results(request_url, "GET")

        for policy in response:
            if policy_name == policy.get("name"):
                return policy["id"]
        raise CiscoFirepowerManagerError(
            f'Policy with name "{policy_name}" was not found.'
        )

    def get_rule_by_id(self, policy_id, rule_object_id):
        """
        Get rule object by it's id.
        :param policy_id: policy id {string}
        :param rule_object_id: rule object id {string}
        :return: rule object {dict}
        """
        request_url = urllib.parse.urljoin(
            self.api_root,
            GET_RULE_URL.format(self.domain_uuid, policy_id, rule_object_id),
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()

    def get_rules_by_policy_id(self, policy_id):
        """
        Get list of rule objects.
        :param policy_id: policy id {string}
        :return: list of objects when each object represents a rule {list}
        """
        rules_list = []
        request_url = urllib.parse.urljoin(
            self.api_root, GET_RULES_FOR_POLICY_URL.format(self.domain_uuid, policy_id)
        )
        response = self._paginated_results(request_url, "GET")

        for rule_obj in response:
            rules_list.append(self.get_rule_by_id(policy_id, rule_obj["id"]))

        return rules_list

    def get_rule_by_url(self, policy_id, url):
        """
        Get rule by url that it blocks.
        :param policy_id: container policy id {string}
        :param url: URL {string}
        :return: rule_object {dict}
        """
        rules = self.get_rules_by_policy_id(policy_id)
        for rule in rules:
            urls = rule.get("urls")
            if urls and urls.get("literals"):
                for url_obj in urls.get("literals"):
                    if url_obj.get("url") == url:
                        return rule

    def get_block_url_available_rule(self, rule_objects_list, max_urls_per_rule):
        """
        Fetch rule with less urls then the max ber from a list of rules object.
        :param rule_objects_list: list of dicts when each dict represent a rule object {list}
        :param max_urls_per_rule: Maximum amount of urls per rule {integer}
        :return: rule object {dict}
        """
        for rule in rule_objects_list:
            urls = rule.get("urls")
            # If not 'urls' section at the rule object create it and return the rule(means the rule is empty).
            if not urls or not urls.get("literals"):
                rule["urls"] = copy.deepcopy(RULE_URL_PATTERN)
                return rule
            else:
                url_objects = urls.get("literals")
                if not len(url_objects) < max_urls_per_rule:
                    return rule

    def update_rule(self, policy_id, rule_object):
        """
        Update a rule object.
        :param policy_id: container policy id {string}
        :param rule_object: rule object dict {dict}
        :return: is succeed {bool}
        """
        request_url = urllib.parse.urljoin(
            self.api_root,
            GET_RULE_URL.format(self.domain_uuid, policy_id, rule_object["id"]),
        )
        response = self.session.put(request_url, json=rule_object)
        self.validate_response(response)
        return True

    def get_url_group_obj_by_id(self, url_group_id):
        """
        Get url group objet by it's id.
        :param url_group_id: url group id {string}
        :return: url group object {dict}
        """
        request_url = urllib.parse.urljoin(
            self.api_root,
            GET_URL_GROUP_OBJECT_URL.format(self.domain_uuid, url_group_id),
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()

    def get_url_group_by_name(self, url_group_name):
        """
        Get url group object by it's name.
        :param url_group_name: url group name {string}
        :return: url group object {dict}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, GET_URL_GROUPS_URL.format(self.domain_uuid)
        )
        response = self._paginated_results(request_url, "GET")
        for url_group_obj in response:
            if url_group_name == url_group_obj.get("name"):
                return self.get_url_group_obj_by_id(url_group_obj.get("id"))

        raise CiscoFirepowerManagerError(
            f'Not found url group with name: "{url_group_name}"'
        )

    def block_url(self, url_group_object, url):
        """
        Block a url.
        :param url: url to block {string}
        :param url_group_object: url group object {dict}
        :return: is succeed {bool}
        """
        # Create literal, it is an object that has to be appended to the url group.
        literal = copy.deepcopy(RULE_LITERAL_OBJECT)
        literal["url"] = url

        payload = copy.deepcopy(UPDATE_URL_GROUP_PAYLOAD)
        payload["id"] = url_group_object["id"]
        payload["name"] = url_group_object["name"]
        payload["literals"] = url_group_object.get("literals")

        # Check if there is literal key in url group else add it.
        if not payload.get("literals"):
            payload["literals"] = [literal]
        else:
            payload["literals"].append(literal)

        # Update Url group.
        request_url = urllib.parse.urljoin(
            self.api_root,
            GET_URL_GROUP_OBJECT_URL.format(self.domain_uuid, url_group_object["id"]),
        )

        response = self.session.put(request_url, json=payload)
        self.validate_response(response)

        return True

    def unblock_url(self, url_group_object, url):
        """
        Unblock url.
        :param url_group_object: {string}
        :param url: URL to unblock  {string}
        :return: is succeed {bool}
        """
        payload = copy.deepcopy(UPDATE_URL_GROUP_PAYLOAD)
        payload["id"] = url_group_object["id"]
        payload["name"] = url_group_object["name"]
        payload["literals"] = url_group_object.get("literals")

        if payload.get("literals"):
            for literal in payload["literals"]:
                if literal.get("url") == url:
                    payload["literals"].remove(literal)
            request_url = urllib.parse.urljoin(
                self.api_root,
                GET_URL_GROUP_OBJECT_URL.format(
                    self.domain_uuid, url_group_object["id"]
                ),
            )

            response = self.session.put(request_url, json=payload)
            self.validate_response(response)

        return True

    def create_port_object(self, port_protocol, port):
        """
        Create a port object.
        :param port_protocol: {string}
        :param port:  {string}
        :return: {dict}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, CREATE_PORT_OBJECT_URL.format(self.domain_uuid)
        )

        payload = copy.deepcopy(CREATE_PORT_OBJECT_PAYLOAD)
        payload["name"] = payload["name"].format(port)
        payload["port"] = port
        payload["protocol"] = port_protocol

        response = self.session.post(request_url, json=payload)
        self.validate_response(response)

        return response.json()

    def get_port_group_object_by_id(self, port_group_id):
        """
        Get port group id by id.
        :param port_group_id: {string}
        :return: port group object {dict}
        """
        request_url = urllib.parse.urljoin(
            self.api_root,
            GET_PORT_GROUP_OBJECT_URL.format(self.domain_uuid, port_group_id),
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()

    def get_port_group_object_by_name(self, port_group_name):
        """
        Get port group object by it's name.
        :param port_group_name: port group name {string}
        :return:
        """
        request_url = urllib.parse.urljoin(
            self.api_root, GET_ALL_PORT_GROUP_OBJECTS_URL.format(self.domain_uuid)
        )

        response =self._paginated_results(request_url, "GET")

        for port_group_obj in response.json()["items"]:
            if port_group_obj.get("name") == port_group_name:
                return self.get_port_group_object_by_id(port_group_obj["id"])

        raise CiscoFirepowerManagerError(
            f'Not found port group object with name: "{port_group_name}"'
        )

    def get_port_object_by_id(self, port_object_id):
        """
        Get port object by id.
        :param port_object_id: port object id {string}
        :return: port object {dict}
        """
        request_url = urllib.parse.urljoin(
            self.api_root,
            GET_PORT_OBJECT_BY_ID_URL.format(self.domain_uuid, port_object_id),
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()

    def delete_port_object_by_id(self, port_object_id):
        """
        Get port object by id.
        :param port_object_id: port object id {string}
        :return: port object {dict}
        """
        request_url = urllib.parse.urljoin(
            self.api_root,
            GET_PORT_OBJECT_BY_ID_URL.format(self.domain_uuid, port_object_id),
        )
        response = self.session.delete(request_url)
        self.validate_response(response)
        return response.json()

    def block_port(self, port_group_object, port_protocol, port):
        """
        Block a port.
        :param port_group_object: {string}
        :param port_protocol: {string}
        :param port: {string}
        :return: is succeed  {bool}
        """
        request_url = urllib.parse.urljoin(
            self.api_root,
            GET_PORT_GROUP_OBJECT_URL.format(self.domain_uuid, port_group_object["id"]),
        )

        # Check if already blocked, if yes return True.
        for port_object in port_group_object["objects"]:
            if port == port_object["port"]:
                return True

        # Create port object.
        port_object = self.create_port_object(port_protocol, port)
        port_object_for_payload = copy.deepcopy(PORT_OBJECT_STRUCTURE)
        port_object_for_payload["id"] = port_object["id"]
        port_object_for_payload["port"] = port_object["port"]

        payload = copy.deepcopy(UPDATE_PORT_GROUP_PAYLOAD)

        payload["objects"] = port_group_object["objects"]
        payload["objects"].append(port_object_for_payload)
        payload["id"] = port_group_object["id"]
        payload["name"] = port_group_object["name"]

        response = self.session.put(request_url, json=payload)
        self.validate_response(response)
        return True

    def unblock_port(self, port_group_object, port):
        """
        Unblock port.
        :param port_group_object: port group object {dict}
        :param port: port {string}
        :return: is succeed {bool}
        """
        request_url = urllib.parse.urljoin(
            self.api_root,
            GET_PORT_GROUP_OBJECT_URL.format(self.domain_uuid, port_group_object["id"]),
        )
        object_to_remove = None
        for object in port_group_object["objects"]:
            if object.get("port") == port:
                object_to_remove = object
                port_group_object["objects"].remove(object)
                break

        # if port does not exist return True(Already not blocked).
        if not object_to_remove:
            return True

        # Arrange port objects for payload.
        for object in port_group_object["objects"]:
            for key in list(object.keys()):
                if not key == "id" and not key == "type":
                    object.pop(key)

        payload = copy.deepcopy(UPDATE_PORT_GROUP_PAYLOAD)
        payload["objects"] = port_group_object["objects"]
        payload["id"] = port_group_object["id"]
        payload["name"] = port_group_object["name"]

        response = self.session.put(request_url, json=payload)

        self.validate_response(response)

        # delete unblocked port object.
        self.delete_port_object_by_id(object_to_remove["id"])

        return True

    def get_network_group_object_by_id(self, network_group_id):
        """
        Get a network object dict by id.
        :param network_group_id: network group id {string}
        :return: network group object {dict}
        """
        request_url = urllib.parse.urljoin(
            self.api_root,
            GET_NETWORK_GROUP_OBJECT_BY_ID_URL.format(
                self.domain_uuid, network_group_id
            ),
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()

    def get_network_group_object_by_name(self, network_group_name):

        request_url = urllib.parse.urljoin(
            self.api_root, GET_NETWORK_GROUP_OBJECTS_URL.format(self.domain_uuid)
        )
        network_objects = self._paginated_results(request_url, "GET")

        for network_object in network_objects:
            if network_object.get("name") == network_group_name:
                return self.get_network_group_object_by_id(network_object.get("id"))

        raise CiscoFirepowerManagerError(
            f'Not found network object with name "{network_group_name}"'
        )

    def block_ip_address(self, network_group_object, ip_address):
        """
        Block IP address.
        :param network_group_object: network group object {dict}
        :param ip_address: ip address to block  {string}
        :return: is succeed {bool}
        """
        request_url = urllib.parse.urljoin(
            self.api_root,
            GET_NETWORK_GROUP_OBJECT_BY_ID_URL.format(
                self.domain_uuid, network_group_object["id"]
            ),
        )

        # check if already blocked.
        if network_group_object.get("literals"):
            for literal in network_group_object["literals"]:
                if literal.get("value") == ip_address:
                    return True
        else:
            # if object contains no literals, create an empty list.
            network_group_object["literals"] = []

        # payload.
        # Has the same payload as the url function.
        payload = copy.deepcopy(UPDATE_URL_GROUP_PAYLOAD)
        payload["name"] = network_group_object["name"]
        payload["id"] = network_group_object["id"]
        payload["literals"] = network_group_object["literals"]
        # Build ip address literal and append it to the network object.
        ip_address_literal = copy.deepcopy(IP_ADDRESS_LITERAL_PATTERN)
        ip_address_literal["value"] = ip_address
        payload["literals"].append(ip_address_literal)

        response = self.session.put(request_url, json=payload)

        self.validate_response(response)

        return True

    def unblock_ip_address(self, network_group_object, ip_address):
        """
        Unlock IP address.
        :param network_group_object: network group object {dict}
        :param ip_address: ip address to block  {string}
        :return: is succeed {bool}
        """
        request_url = urllib.parse.urljoin(
            self.api_root,
            GET_NETWORK_GROUP_OBJECT_BY_ID_URL.format(
                self.domain_uuid, network_group_object["id"]
            ),
        )

        # check if already blocked.
        if network_group_object.get("literals"):
            for literal in network_group_object["literals"]:
                if literal.get("value") == ip_address:
                    network_group_object["literals"].remove(literal)
        else:
            # No literals means that ip already unblocked.
            return True

        # payload.
        # Has the same payload as the url function.
        payload = copy.deepcopy(UPDATE_URL_GROUP_PAYLOAD)
        payload["name"] = network_group_object["name"]
        payload["id"] = network_group_object["id"]
        payload["literals"] = network_group_object["literals"]

        # Request cannot receive an empty list(push dummy literal.
        if not payload["literals"]:
            raise CiscoFirepowerManagerError(
                "Network group can not be empty, at least one address has to be blocked."
            )

        response = self.session.put(request_url, json=payload)

        self.validate_response(response)

        return True

    def _paginated_results(
        self,
        url: str,
        method: str,
        params: dict[str, Any] | None = None,
        limit: int = PAGINATION_LIMIT ,
    ) -> list[dict[str, Any]]:
        """Fetch paginated results from Cisco Firepower Management Center API.

        Args:
            url: URL of the Firepower Management Center API
            method: HTTP method (GET, POST, etc.)
            params: Additional query parameters
            limit: Maximum number of items to retrieve (default: 1000)

        Returns:
            List of all items retrieved from paginated requests
        """
        all_results: list[dict[str, Any]] = []
        offset: int = 0
        page_size: int = PAGE_SIZE
        params: dict[str, Any] | None = params or {}

        while len(all_results) < limit:
            params["limit"] = min(page_size, limit - len(all_results))
            params["offset"] = offset

            response = self.session.request(method, url, params=params)
            self.validate_response(response)

            data = response.json()
            items = data.get("items", [])

            if not items:
                break

            all_results.extend(items)
            offset += len(items)

            if len(items) < page_size:
                break

        return all_results
