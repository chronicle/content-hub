from __future__ import annotations
from typing import Dict, List
from urllib.parse import urljoin
import requests
from .CloudflareExceptions import (
    ZoneNotFoundException,
    AccountNotFoundException,
    RuleListNotFoundException,
)
from .CloudflareParser import CloudflareParser
from .UtilsManager import validate_response
from .constants import ENDPOINTS, EQUAL
from .datamodels import RuleList


class CloudflareManager:
    def __init__(
        self, api_root, api_token, verify_ssl, account_name="", siemplify_logger=None
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} Cloudflare API root
        :param api_token: {str} Cloudflare API token
        :param verify_ssl: {bool} Specifies if certificate that is configured on the api root should be validated
        :param siemplify_logger: Siemplify logger
        :param account_name: Cloudflare Account name
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.account_name = account_name
        self.verify_ssl = verify_ssl
        self.siemplify_logger = siemplify_logger
        self.parser = CloudflareParser()
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update({"Authorization": f"Bearer {api_token}"})
        self.account_id = self._get_account_id(account_name) if account_name else None

    def _get_full_url(self, url_id, **kwargs) -> str:
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
        :return: {void}
        """
        url = self._get_full_url("ping", account_name=self.account_name)
        response = self.session.get(url)
        validate_response(response)
        result = self.parser.extract_data_from_raw_data(response.json())
        if not result:
            raise AccountNotFoundException(
                "Invalid account name was provided. Please check the spelling."
            )

    def get_zone(self, zone_name):
        """
        Find zone with the name
        :param zone_name: {str} Name of the zone
        :return: {obj} Zone object
        """
        url = self._get_full_url("get_zone")
        params = {"name": zone_name}
        response = self.session.get(url, params=params)
        try:
            validate_response(response)
            results = self.parser.build_results(response.json(), "build_zone_object")
            if results:
                return results[0]
            else:
                raise
        except:
            raise ZoneNotFoundException(f"zone {zone_name} wasn't found in Cloudflare.")

    def _get_account_id(self, account_name: str) -> str:
        """
        Args:
            account_name: str
        Returns:
            str
        """
        error_message = f"Invalid account name was provided. Please check the spelling."
        url = self._get_full_url("get_account")
        params = {"name": account_name}

        raw_account = self._paginate_results(
            "GET", url, params=params, err_msg=error_message
        )
        if raw_account:
            return raw_account[0]["id"]
        raise AccountNotFoundException(error_message)

    def create_rule_list(self, name: str, rule_list_type: str, description: str):
        """
        Creates Rule List with given arguments

        Args:
            name: Name of the Rule List
            rule_list_type: Type of the Rule List
            description: Summary of the Rule List.

        Returns:
            Returns Rule List object
        """
        url = self._get_full_url("rule_list", account_id=self.account_id)
        response = self.session.post(
            url, json={"name": name, "kind": rule_list_type, "description": description}
        )
        validate_response(response)
        rule_list_object = self.parser.build_rule_list_object(
            self.parser.extract_data_from_raw_data(response.json())
        )
        return rule_list_object

    def list_firewall_rules(
        self, zone_id, filter_key, filter_logic, filter_value, limit=None
    ):
        """
        Get firewall rules list
        :param zone_id: {str} Zone id to fetch results from
        :param filter_key: {str} Filter key
        :param filter_logic: {str} Filter logic
        :param filter_value: {str} Filter value
        :param limit: {str} Filtered items limit
        :return: {list}
        """
        url = self._get_full_url("get_firewall_rules", zone_id=zone_id)

        if filter_logic and filter_logic == EQUAL:
            params = {filter_key: filter_value}
        else:
            params = {}

        raw_list = self._paginate_results(
            "GET", url, params=params, limit=limit, err_msg="Unable to get rules"
        )

        return self.parser.build_filtered_obj_list(
            self.parser.build_results(
                raw_list, "build_firewall_rule_object", pure_data=True
            ),
            filter_key,
            filter_logic,
            filter_value,
            limit,
        )

    def _paginate_results(
        self,
        method,
        url,
        params=None,
        body=None,
        page=1,
        limit=None,
        err_msg="Unable to get results",
    ):
        """
        Paginate the results of a job
        :param method: {str} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {str} The url to send request to
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param page: {int} The page of the results to fetch
        :param limit: {int} The limit of the results to fetch
        :param err_msg: {str} The message to display on error
        :return: {list} List of results
        """
        if params is None:
            params = {}
        params.update({"page": page})
        response = self.session.request(method, url, params=params, json=body)
        validate_response(response, err_msg)
        response_json = response.json()
        results = self.parser.extract_data_from_raw_data(response_json)

        while True:
            if limit and len(results) >= limit:
                break
            if len(results) >= response_json.get("result_info", {}).get(
                "total_count", 0
            ):
                break
            page += 1
            params.update({"page": page})
            response = self.session.request(method, url, params=params, json=body)
            validate_response(response, err_msg)
            response_json = response.json()
            results.extend(self.parser.extract_data_from_raw_data(response_json))

        return results[:limit] if limit else results

    def get_rule_lists(self) -> List[RuleList]:
        """
        Gets all available Rule Lists from Cloudflare
        Returns:
            List of RuleList objects
        """
        url = self._get_full_url("rule_list", account_id=self.account_id)

        raw_list = self._paginate_results("GET", url, err_msg="Unable to get rules")
        return self.parser.build_results(
            raw_list, "build_rule_list_object", pure_data=True
        )

    def get_rule_list(self, rule_name: str) -> RuleList:
        """
        Gets all available rule lists and filters it by given rule name

        Args:
            rule_name: Name of searched Rule List

        Returns:
            RuleList object
        """
        rule_lists = self.get_rule_lists()
        for rule_list in rule_lists:
            if rule_name == rule_list.name:
                return rule_list
        raise RuleListNotFoundException(
            f"Rule list {rule_name} wasn't found in Cloudflare."
        )

    def add_url_to_rule_list(self, rule_id: str, rule_list_item_payload: Dict) -> None:
        """
        Adds Rule List Item based on rule_list_item_payload to the Rule List with given rule_id

        Args:
            rule_id: ID of Rule List
            rule_list_item_payload: Information about new Rule List Item

        Returns:
            RuleListItem object
        """
        url = self._get_full_url(
            "rule_list_items", account_id=self.account_id, rule_id=rule_id
        )

        rule_list_item_payload = {
            k: v for k, v in rule_list_item_payload.items() if v is not None
        }

        json_payload = {"redirect": rule_list_item_payload}

        if rule_list_item_payload.get("comment"):
            json_payload["comment"] = rule_list_item_payload.get("comment")
            rule_list_item_payload.pop("comment")

        response = self.session.post(url, json=[json_payload])
        validate_response(response)
        return self.parser.build_rule_list_item_object(response.json())

    def create_firewall_rule(
        self,
        zone_id,
        action,
        expression,
        name=None,
        products=None,
        priority=None,
        reference_tag=None,
    ):
        """
        Create firewall rule
        :param zone_id: {str} zone id to add firewall rule
        :param action: {str} action for firewall rule
        :param expression: {str} expression for firewall rule
        :param name: {str} name for firewall rule
        :param products: {[str]} list of products for firewall rule
        :param priority: {str} priority for firewall rule
        :param reference_tag: {str} reference tag for firewall rule
        :return: {FirewallRule} FirewallRule object
        """
        url = self._get_full_url("create_firewall_rule", zone_id=zone_id)
        payload = {
            "action": action,
            "products": products,
            "priority": priority,
            "description": name,
            "ref": reference_tag,
            "filter": {"expression": expression},
        }

        response = self.session.post(
            url, json=[{key: value for key, value in payload.items() if value}]
        )
        validate_response(response)
        return self.parser.build_results(response.json(), "build_firewall_rule_object")

    def add_ip_to_rule_list(self, rule_id, description, entity_identifier):
        """
        Args:
            rule_id: ID of Rule List which going to be updated
            description: comment to IP address to add
            entity_identifier: IP address to add
        Returns:
            RuleListItem object
        """
        url = self._get_full_url(
            "rule_list_items", account_id=self.account_id, rule_id=rule_id
        )
        payload = {"ip": entity_identifier, "comment": description}
        response = self.session.post(
            url, json=[{key: value for key, value in payload.items() if value}]
        )
        validate_response(response)
        return self.parser.build_rule_list_item_object(response.json())

    def update_firewall_rule(
        self,
        zone_id,
        rule_id,
        rule_name=None,
        action=None,
        filter=None,
        products=None,
        priority=None,
        reference_tag=None,
    ):
        """
        Update firewall rule
        :param zone_id: {str} zone id which contain firewall rule
        :param rule_id: {str} rule id to update
        :param rule_name: {str} rule name
        :param action: {str} action for firewall rule
        :param filter: {dict} filter object for firewall rule
        :param products: {[str]} list of products for firewall rule
        :param priority: {str} priority for firewall rule
        :param reference_tag: {str} reference tag for firewall rule
        :return: {FirewallRule} FirewallRule object
        """
        url = self._get_full_url(
            "manage_firewall_rule", zone_id=zone_id, rule_id=rule_id
        )
        payload = {
            "description": rule_name,
            "action": action,
            "products": products,
            "priority": priority,
            "ref": reference_tag,
            "filter": filter,
        }

        response = self.session.put(
            url, json={key: value for key, value in payload.items() if value}
        )
        validate_response(response)
        return self.parser.build_firewall_rule_object(response.json().get("result", {}))

    def update_firewall_filter(self, zone_id, filter_id, expression):
        """
        Update firewall filter
        :param zone_id: {str} zone id which contain firewall rule
        :param filter_id: {str} firewall filter id
        :param expression: {dict} firewall filter expression
        :return: {FirewallFilter} FirewallFilter object
        """
        url = self._get_full_url(
            "update_firewall_filter", zone_id=zone_id, filter_id=filter_id
        )
        payload = {"id": filter_id, "expression": expression}

        response = self.session.put(url, json=payload)
        validate_response(response)
        return self.parser.build_firewall_filter_object(
            response.json().get("result", {})
        )

    def get_firewall_rule(self, zone_id, rule_id):
        """
        Get firewall rule
        :param zone_id: {str} zone id which contain firewall rule
        :param rule_id: {str} rule id
        :return: {FirewallRule} FirewallRule object
        """
        url = self._get_full_url(
            "manage_firewall_rule", zone_id=zone_id, rule_id=rule_id
        )
        response = self.session.get(url)
        validate_response(response)
        return self.parser.build_firewall_rule_object(response.json().get("result", {}))
