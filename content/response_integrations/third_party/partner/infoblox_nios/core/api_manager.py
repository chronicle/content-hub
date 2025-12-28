from __future__ import annotations

import time
import urllib.parse
from typing import Any, Dict, List, Optional

import requests
from requests.auth import HTTPBasicAuth

from ..core.utils import (
    HandleExceptions,
    clean_params,
    create_rpz_rule_name,
    parse_extended_attributes,
    parse_extended_attributes_to_dict,
)
from .constants import (
    CREATE_HOST_RECORD_ACTION_IDENTIFIER,
    CREATE_RESPONSE_POLICY_ZONE_ACTION_IDENTIFIER,
    CREATE_RPZ_CNAME_ACTION_IDENTIFIER,
    CREATE_RPZ_CNAME_ACTION_IDENTIFIER_CLIENT_IP,
    CREATE_RPZ_CNAME_ACTION_IDENTIFIER_IP,
    CREATE_RPZ_MX_RULE_ACTION_IDENTIFIER,
    CREATE_RPZ_NAPTR_RULE_ACTION_IDENTIFIER,
    CREATE_RPZ_PTR_RULE_ACTION_IDENTIFIER,
    CREATE_RPZ_SRV_RULE_ACTION_IDENTIFIER,
    CREATE_RPZ_TXT_RULE_ACTION_IDENTIFIER,
    DEFAULT_PAGE_SIZE,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_RESULTS_LIMIT,
    DELETE_RESPONSE_POLICY_ZONE_ACTION_IDENTIFIER,
    DELETE_RPZ_RULE_ACTION_IDENTIFIER,
    DHCP_LEASE_LOOKUP_ACTION_IDENTIFIER,
    ENDPOINTS,
    GET_RESPONSE_POLICY_ZONE_DETAILS_ACTION_IDENTIFIER,
    IP_LOOKUP_ACTION_IDENTIFIER_V4,
    IP_LOOKUP_ACTION_IDENTIFIER_V6,
    LIST_HOST_INFO_ACTION_IDENTIFIER,
    LIST_NETWORK_INFO_ACTION_IDENTIFIER,
    PING_ACTION_IDENTIFIER,
    RATE_LIMIT_EXCEEDED_STATUS_CODE,
    RETRY_COUNT,
    RETURN_FIELDS,
    SEARCH_RPZ_RULE_ACTION_IDENTIFIER,
    UPDATE_RPZ_CNAME_ACTION_IDENTIFIER,
    WAIT_TIME_FOR_RETRY,
)
from .infoblox_exceptions import RateLimitException


class APIManager:
    def __init__(
        self,
        api_root: str,
        username: str,
        password: str,
        verify_ssl: bool = False,
        siemplify: Optional[Any] = None,
    ) -> None:
        """
        Initializes an object of the APIManager class.

        Args:
            api_root (str): API root of the Infoblox server.
            username (str): Username of the Infoblox account.
            password (str): Password of the Infoblox account.
            verify_ssl (bool, optional): If True, verify the SSL certificate for the connection.
                Defaults to False.
            siemplify (object, optional): An instance of the SDK SiemplifyConnectorExecution class.
                Defaults to None.
        """
        self.api_root = api_root
        self.username = username
        self.password = password
        self.siemplify = siemplify
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.auth = HTTPBasicAuth(username, password)

    def _get_full_url(self, url_id: str, **kwargs: Any) -> str:
        """
        Get full URL from URL identifier.

        Args:
            url_id (str): The ID of the URL.
            kwargs (dict): Variables passed for string formatting.

        Returns:
            str: The full URL.
        """
        return urllib.parse.urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def _get_return_fields(self, api_identifier: str) -> str:
        """
        Get return fields for the API identifier.

        Args:
            api_identifier (str): API identifier.

        Returns:
            str: Comma separated string of return fields.
        """
        return ",".join(RETURN_FIELDS.get(api_identifier, []))

    def _paginator(
        self,
        api_name: str,
        method: str,
        url: str,
        result_key: str = "result",
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        limit: int = DEFAULT_RESULTS_LIMIT,
    ) -> List[Dict[str, Any]]:
        """
        Paginate results using Infoblox WAPI paging (_paging, _max_results, _page_id).

        Args:
            api_name (str): API name.
            method (str): The method of the request (GET, POST, etc.).
            url (str): The URL to send the request to.
            result_key (str, optional): The key to extract data. Defaults to "result" for Infoblox.
            params (dict, optional): The parameters of the request.
            body (dict, optional): The JSON payload of the request.
            limit (int, optional): The limit of the results. Defaults to DEFAULT_RESULTS_LIMIT.

        Returns:
            list: List of results.
        """
        limit = limit or DEFAULT_RESULTS_LIMIT
        params = params.copy() if params else {}

        # Infoblox WAPI paging params
        params["_paging"] = 1
        params["_return_as_object"] = 1
        page_size = DEFAULT_PAGE_SIZE if limit >= DEFAULT_PAGE_SIZE else limit
        params["_max_results"] = page_size

        results = []
        page_id = None

        while True:
            if page_id:
                params["_page_id"] = page_id
            else:
                params.pop("_page_id", None)  # Remove if present

            try:
                response = self._make_rest_call(api_name, method, url, params=params, body=body)
            except Exception:
                raise

            page_results = response.get(result_key, [])
            results.extend(page_results)

            # Check for next_page_id
            page_id = response.get("next_page_id")
            if not page_id or len(results) >= limit:
                break

            remaining = limit - len(results)
            params["_max_results"] = min(DEFAULT_PAGE_SIZE, remaining)
        # Return only up to the requested limit
        return results[:limit]

    def _make_rest_call(
        self,
        api_identifier: str,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        retry_count: int = RETRY_COUNT,
    ) -> Dict[str, Any]:
        """
        Make a rest call to the Infoblox.

        Args:
            api_identifier (str): API Identifier.
            method (str): The method of the request (GET, POST, etc.).
            url (str): The URL to send the request to.
            params (dict, optional): The parameters of the request. Defaults to None.
            body (dict, optional): The JSON payload of the request. Defaults to None.
            retry_count (int, optional): The number of retries in case of rate limit.
                Defaults to RETRY_COUNT.

        Returns:
            dict: The JSON response from the API.

        Raises:
            RateLimitException: If the API rate limit is exceeded.
        """
        _return_fields = self._get_return_fields(api_identifier)
        if _return_fields:
            params = params or {}
            params["_return_fields"] = _return_fields

        response = self.session.request(
            method, url, params=params, json=body, timeout=DEFAULT_REQUEST_TIMEOUT
        )
        try:
            self.validate_response(api_identifier, response)
        except RateLimitException:
            if retry_count > 0:
                time.sleep(WAIT_TIME_FOR_RETRY)
                retry_count -= 1
                return self._make_rest_call(api_identifier, method, url, params, body, retry_count)
            else:
                raise RateLimitException("API rate limit exceeded.")

        try:
            return response.json()
        except Exception:
            self.siemplify.LOGGER.error(
                "Exception occurred while returning response JSON for API identifier"
                + f"{api_identifier} and URL {url}"
            )
            return {}

    @staticmethod
    def validate_response(
        api_identifier: str, response: requests.Response, error_msg: str = "An error occurred"
    ) -> bool:
        """
        Validate the response from the API.

        Args:
            api_identifier (str): API name.
            response (requests.Response): The response object.
            error_msg (str, optional): The error message to display. Defaults to "An error occurred"

        Returns:
            bool: True if the response is valid, raises an exception otherwise.

        Raises:
            RateLimitException: If the API rate limit is exceeded.
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            if response.status_code == RATE_LIMIT_EXCEEDED_STATUS_CODE:
                raise RateLimitException("API rate limit exceeded.")

            HandleExceptions(api_identifier, error, response, error_msg).do_process()

        return True

    def test_connectivity(self) -> bool:
        """
        Test connectivity to the Infoblox.

        Returns:
            bool: True if successful, exception otherwise.
        """
        request_url = self._get_full_url(PING_ACTION_IDENTIFIER)
        _ = self._make_rest_call(PING_ACTION_IDENTIFIER, "GET", request_url)
        return True

    def delete_response_policy_zone(self, reference_id: str) -> Dict[str, Any]:
        """
        Delete a Response Policy Zone (RPZ) by reference ID.

        Args:
            reference_id (str): The reference ID of the RPZ to remove.
        Returns:
            dict: API response (empty on success or reference of deleted object).
        Raises:
            InfobloxException: If the RPZ does not exist (404) or other errors.
        """
        url = self._get_full_url(
            DELETE_RESPONSE_POLICY_ZONE_ACTION_IDENTIFIER, reference_id=reference_id
        )
        response = self._make_rest_call(
            DELETE_RESPONSE_POLICY_ZONE_ACTION_IDENTIFIER, "DELETE", url
        )
        return response

    def delete_rpz_rule(self, reference_id: str) -> Dict[str, Any]:
        """
        Delete a RPZ Rule by reference ID.

        Args:
            reference_id (str): The reference ID of the RPZ Rule to remove.
        Returns:
            dict: API response (empty on success or reference of deleted object).
        Raises:
            InfobloxException: If the RPZ Rule does not exist (404) or other errors.
        """

        url = self._get_full_url(DELETE_RPZ_RULE_ACTION_IDENTIFIER, reference_id=reference_id)
        response = self._make_rest_call(DELETE_RPZ_RULE_ACTION_IDENTIFIER, "DELETE", url)
        return response

    def search_rpz_rule(
        self, object_type: str, rule_name: str, output_fields: str, limit: int
    ) -> List[Dict[str, Any]]:
        """
        Search RPZ Rules by name.

        Args:
            object_type (str): The type of the object to search for.
            rule_name (str): The name of the rule to search for.
            output_fields (str): The fields to return in the response.
            limit (int): The maximum number of results to return.
        Returns:
            List: List of RPZ Rules.
        Raises:
            InfobloxException: If the RPZ Rule does not exist (404) or other errors.
        """

        url = self._get_full_url(SEARCH_RPZ_RULE_ACTION_IDENTIFIER, object_type=object_type)
        params = {"name": rule_name, "_return_fields": output_fields}

        params = clean_params(params)

        response = self._paginator(
            SEARCH_RPZ_RULE_ACTION_IDENTIFIER, "GET", url, params=params, limit=limit
        )
        return response

    def ip_lookup(
        self,
        ip_address: Optional[str],
        network: Optional[str],
        from_ip: Optional[str],
        to_ip: Optional[str],
        ip_status: Optional[str],
        extended_attributes: Optional[str],
        limit: int = DEFAULT_RESULTS_LIMIT,
    ) -> List[Dict[str, Any]]:
        """
        Look up an IP address in the Infoblox.

        Args:
            ip_address (str): The IP address to look up.

        Returns:
            dict: API response containing the IP address details.
        """
        params = {
            "ip_address": ip_address,
            "network": network,
            "ip_address>": from_ip,
            "ip_address<": to_ip,
            "status": ip_status if ip_status != "ALL" else None,
        }
        params = clean_params(params)
        if extended_attributes:
            params.update(parse_extended_attributes(extended_attributes))
        ip_lookup_identifier = (
            IP_LOOKUP_ACTION_IDENTIFIER_V4
            if ":"
            not in (
                params.get("ip_address", "")
                + params.get("network", "")
                + params.get("ip_address>", "")
                + params.get("ip_address<", "")
            )
            else IP_LOOKUP_ACTION_IDENTIFIER_V6
        )
        url = self._get_full_url(ip_lookup_identifier, ip_address=ip_address)
        response = self._paginator(
            api_name=ip_lookup_identifier,
            method="GET",
            url=url,
            params=params,
            limit=limit,
        )
        return response

    def get_rp_zone_details(
        self, fqdn: Optional[str], view: Optional[str], comment: Optional[str], limit: int
    ) -> List[Dict[str, Any]]:
        """
        Retrieve Response Policy Zones (RPZ) with optional filtering.

        Args:
            fqdn (str): The FQDN to filter by.
            view (str): The DNS view to filter by.
            comment (str): Comment to filter by (supports partial match).
            limit (int): Max number of results to return.

        Returns:
            list: List of RPZ zone dicts.
        """
        url = self._get_full_url(GET_RESPONSE_POLICY_ZONE_DETAILS_ACTION_IDENTIFIER)
        params = {"fqdn": fqdn, "view": view, "comment": comment}
        params = clean_params(params)
        response = self._paginator(
            api_name=GET_RESPONSE_POLICY_ZONE_DETAILS_ACTION_IDENTIFIER,
            method="GET",
            url=url,
            params=params,
            limit=limit,
        )

        return response

    def list_network_info(
        self,
        network: Optional[str],
        extended_attributes: Optional[str],
        limit: int = DEFAULT_RESULTS_LIMIT,
    ) -> List[Dict[str, Any]]:
        """
        List network information.

        Args:
            network (str): The network to list.
            extended_attributes (str): The extended attributes to return.
            limit (int): The limit of the results.

        Returns:
            list: List of network information.
        """
        url = self._get_full_url(LIST_NETWORK_INFO_ACTION_IDENTIFIER)
        params = {"network": network}
        params = clean_params(params)
        if extended_attributes:
            params.update(parse_extended_attributes(extended_attributes))

        response = self._paginator(
            api_name=LIST_NETWORK_INFO_ACTION_IDENTIFIER,
            method="GET",
            url=url,
            params=params,
            limit=limit,
            result_key="result",
        )

        return response

    def create_rpz_txt_rule(
        self,
        rp_zone: str,
        name: str,
        text: str,
        comment: Optional[str],
        additional_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a new RPZ TXT rule.

        Args:
            rp_zone (str): The RP zone to create the rule in.
            name (str): The name of the rule.
            text (str): The text of the rule.
            comment (str): The comment of the rule.
            additional_params (str): The additional parameters of the rule.

        Returns:
            dict: The created rule.
        """

        url = self._get_full_url(CREATE_RPZ_TXT_RULE_ACTION_IDENTIFIER)
        body = {
            **additional_params,
            "rp_zone": rp_zone,
            "name": create_rpz_rule_name(name, rp_zone),
            "text": text,
            "comment": comment,
        }

        body = clean_params(body)

        response = self._make_rest_call(
            CREATE_RPZ_TXT_RULE_ACTION_IDENTIFIER, "POST", url, body=body
        )

        return response

    def dhcp_lease_lookup(
        self,
        ip_address: Optional[str],
        hardware: Optional[str],
        hostname: Optional[str],
        ipv6_duid: Optional[str],
        fingerprint: Optional[str],
        username: Optional[str],
        protocol: str = "BOTH",
        limit: int = DEFAULT_RESULTS_LIMIT,
    ) -> List[Dict[str, Any]]:
        """
        Look up a DHCP lease in the Infoblox.

        Args:
            ip_address (str): The IP address to look up.

        Returns:
            dict: API response containing the DHCP lease details.
        """
        params = {
            "address": ip_address,
            "hardware~": hardware,
            "client_hostname~": hostname,
            "ipv6_duid~": ipv6_duid,
            "fingerprint~": fingerprint,
            "username~": username,
            "protocol": protocol,
        }
        params = clean_params(params)
        url = self._get_full_url(DHCP_LEASE_LOOKUP_ACTION_IDENTIFIER)
        response = self._paginator(
            api_name=DHCP_LEASE_LOOKUP_ACTION_IDENTIFIER,
            method="GET",
            url=url,
            params=params,
            limit=limit,
        )
        return response

    def create_rp_zone(
        self,
        fqdn: str,
        rpz_policy: str,
        rpz_severity: str,
        rpz_type: str,
        substitute_name: Optional[str],
        comment: Optional[str],
        fireeye_rule_mapping: Optional[Dict[str, Any]],
        additional_parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a new Response Policy Zone (RPZ) in Infoblox.

        Args:
            fqdn (str): FQDN of the RPZ zone.
            rpz_policy (str): Policy for the RPZ.
            rpz_severity (str): Severity for the RPZ.
            rpz_type (str): Type of the RPZ.
            substitute_name (str, optional): Substitute name for the zone.
            comment (str, optional): Comment for the zone.
            fireeye_rule_mapping (struct, optional): Fire eye rule mapping for the zone.
            additional_parameters (str, optional): JSON string of additional parameters.

        Returns:
            dict: API response.
        """
        url = self._get_full_url(CREATE_RESPONSE_POLICY_ZONE_ACTION_IDENTIFIER)
        body = {
            **additional_parameters,
            "fqdn": fqdn,
            "rpz_policy": rpz_policy,
            "rpz_severity": rpz_severity,
            "rpz_type": rpz_type,
            "substitute_name": substitute_name,
            "comment": comment,
            "fireeye_rule_mapping": fireeye_rule_mapping,
        }
        body = clean_params(body)
        response = self._make_rest_call(
            CREATE_RESPONSE_POLICY_ZONE_ACTION_IDENTIFIER, "POST", url, body=body
        )
        return response

    def create_rpz_a_rule(
        self,
        object_type: str,
        name: str,
        rp_zone: str,
        ipv4addr: str,
        comment: Optional[str],
        additional_parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create an RPZ A rule (Domain Name or IP address) in Infoblox.

        Args:
            object_type (str): "Domain Name" or "IP address"
            name (str): FQDN for the rule.
            rp_zone (str): The RPZ zone name.
            ipv4addr (str): The IPv4 address for substitution/blocking.
            comment (str, optional): Comment.
            additional_parameters (str, optional): JSON string of additional parameters.

        Returns:
            dict: API response.
        """
        body = {
            **additional_parameters,
            "name": create_rpz_rule_name(name, rp_zone),
            "rp_zone": rp_zone,
            "ipv4addr": ipv4addr,
            "comment": comment,
        }
        body = clean_params(body)
        url = self._get_full_url(object_type)

        response = self._make_rest_call(object_type, "POST", url, body=body)
        return response

    def create_rpz_aaaa_rule(
        self,
        object_type: str,
        name: str,
        rp_zone: str,
        ipv6addr: str,
        comment: Optional[str],
        additional_parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create an RPZ A rule (Domain Name or IP address) in Infoblox.

        Args:
            object_type (str): "Domain Name" or "IP address"
            name (str): FQDN for the rule.
            rp_zone (str): The RPZ zone name.
            ipv6addr (str): The IPv6 address for substitution/blocking.
            comment (str, optional): Comment.
            additional_parameters (str, optional): JSON string of additional parameters.

        Returns:
            dict: API response.
        """
        body = {
            **additional_parameters,
            "name": create_rpz_rule_name(name, rp_zone),
            "rp_zone": rp_zone,
            "ipv6addr": ipv6addr,
            "comment": comment,
        }
        body = clean_params(body)
        url = self._get_full_url(object_type)

        response = self._make_rest_call(object_type, "POST", url, body=body)
        return response

    def create_rpz_mx_rule(
        self,
        rp_zone: str,
        name: str,
        mail_exchanger: str,
        preference: int,
        comment: Optional[str],
        additional_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a new RPZ MX rule.

        Args:
            rp_zone (str): The RP zone to create the rule in.
            name (str): The name of the rule.
            mail_exchanger (str): The mail exchanger for the MX rule.
            preference (int): The preference for the MX rule.
            comment (str): The comment for the rule.
            additional_params (dict): Additional parameters for the rule.

        Returns:
            dict: The created rule.
        """
        url = self._get_full_url(CREATE_RPZ_MX_RULE_ACTION_IDENTIFIER)
        body = {
            **additional_params,
            "rp_zone": rp_zone,
            "name": create_rpz_rule_name(name, rp_zone),
            "mail_exchanger": mail_exchanger,
            "preference": preference,
            "comment": comment,
        }

        body = clean_params(body)

        response = self._make_rest_call(
            CREATE_RPZ_MX_RULE_ACTION_IDENTIFIER, "POST", url, body=body
        )

        return response

    def create_rpz_ptr_rule(
        self,
        rp_zone: str,
        ptrdname: str,
        name: Optional[str],
        comment: Optional[str],
        ipv4addr: Optional[str],
        ipv6addr: Optional[str],
        additional_parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a new RPZ PTR rule.

        Args:
            rp_zone (str): The RP zone to create the rule in.
            ptrdname (str): The PTR DName for the rule.
            name (str): The name of the rule (optional).
            comment (str): The comment for the rule (optional).
            ipv4addr (str): The IPv4 address for the rule (optional).
            ipv6addr (str): The IPv6 address for the rule (optional).
            additional_parameters (dict): Additional parameters for the rule.

        Returns:
            dict: The created rule.
        """
        url = self._get_full_url(CREATE_RPZ_PTR_RULE_ACTION_IDENTIFIER)
        body = {
            **additional_parameters,
            "rp_zone": rp_zone,
            "ptrdname": ptrdname,
            "name": create_rpz_rule_name(name, rp_zone) if name else None,
            "comment": comment,
            "ipv4addr": ipv4addr,
            "ipv6addr": ipv6addr,
        }

        body = clean_params(body)

        response = self._make_rest_call(
            CREATE_RPZ_PTR_RULE_ACTION_IDENTIFIER, "POST", url, body=body
        )

        return response

    def list_host_info(
        self,
        name: Optional[str],
        ipv4addrs: Optional[str],
        ipv6addrs: Optional[str],
        extended_attributes: Optional[str],
        limit: int = DEFAULT_RESULTS_LIMIT,
    ) -> List[Dict[str, Any]]:
        """
        List host information.

        Args:
            name (str): The name of the host to list.
            ipv4addrs (str): The IPv4 addresses to list.
            ipv6addrs (str): The IPv6 addresses to list.
            extended_attributes (str): The extended attributes to return.
            limit (int): The limit of the results.

        Returns:
            list: List of host information.
        """
        url = self._get_full_url(LIST_HOST_INFO_ACTION_IDENTIFIER)
        params = {
            "name": name,
            "ipv4addr": ipv4addrs,
            "ipv6addr": ipv6addrs,
        }

        params = clean_params(params)
        if extended_attributes:
            params.update(parse_extended_attributes(extended_attributes))

        response = self._paginator(
            api_name=LIST_HOST_INFO_ACTION_IDENTIFIER,
            method="GET",
            url=url,
            params=params,
            limit=limit,
            result_key="result",
        )

        return response

    def create_rpz_naptr_rule(
        self,
        rp_zone: str,
        name: str,
        order: int,
        preference: int,
        replacement: str,
        comment: Optional[str],
        additional_parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a new RPZ NAPTR rule.

        Args:
            rp_zone (str): The RP zone to create the rule in.
            name (str): The name of the rule.
            order (int): The order of the rule.
            preference (int): The preference of the rule.
            replacement (str): The replacement of the rule.
            comment (str): The comment of the rule.
            additional_parameters (str): The additional parameters of the rule.

        Returns:
            dict: The created rule.
        """
        url = self._get_full_url(CREATE_RPZ_NAPTR_RULE_ACTION_IDENTIFIER)
        body = {
            **additional_parameters,
            "rp_zone": rp_zone,
            "name": create_rpz_rule_name(name, rp_zone),
            "order": order,
            "preference": preference,
            "replacement": replacement,
            "comment": comment,
        }
        body = clean_params(body)

        response = self._make_rest_call(
            CREATE_RPZ_NAPTR_RULE_ACTION_IDENTIFIER, "POST", url, body=body
        )

        return response

    def create_rpz_srv_rule(
        self,
        rp_zone: str,
        name: str,
        priority: int,
        port: int,
        weight: int,
        target: str,
        comment: Optional[str],
        additional_parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a new RPZ SRV rule.

        Args:
            rp_zone (str): The RP zone to create the rule in.
            name (str): The name of the rule.
            priority (int): The priority of the rule.
            port (int): The port of the rule.
            weight (int): The weight of the rule.
            target (str): The target of the rule.
            comment (str): The comment of the rule.
            additional_parameters (str): The additional parameters of the rule.

        Returns:
            dict: The created rule.
        """
        url = self._get_full_url(CREATE_RPZ_SRV_RULE_ACTION_IDENTIFIER)
        body = {
            **additional_parameters,
            "rp_zone": rp_zone,
            "name": create_rpz_rule_name(name, rp_zone),
            "priority": priority,
            "port": port,
            "weight": weight,
            "target": target,
            "comment": comment,
        }
        body = clean_params(body)

        response = self._make_rest_call(
            CREATE_RPZ_SRV_RULE_ACTION_IDENTIFIER, "POST", url, body=body
        )

        return response

    def create_rpz_cname_rule(
        self,
        rule_type: str,
        object_type: str,
        name: str,
        rp_zone: str,
        comment: Optional[str],
        substitute_name: Optional[str],
        view: Optional[str],
        additional_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a CNAME RPZ Rule.
        """
        endpoint_identifier = CREATE_RPZ_CNAME_ACTION_IDENTIFIER
        if object_type == "IP Address":
            endpoint_identifier = CREATE_RPZ_CNAME_ACTION_IDENTIFIER_IP
        elif object_type == "Client IP Address":
            endpoint_identifier = CREATE_RPZ_CNAME_ACTION_IDENTIFIER_CLIENT_IP

        canonical = ""
        if rule_type == "Block (No data)":
            canonical = "*"
        elif rule_type == "Passthru":
            canonical = "rpz-passthru" if object_type == "Client IP Address" else name
        elif rule_type == "Block (No such domain)":
            canonical = ""
        elif rule_type == "Substitute (Domain name)":
            if not substitute_name:
                raise ValueError(
                    "Substitute Name is required for Substitute (Domain name) rule type."
                )
            if object_type == "IP Address" or object_type == "Client IP Address":
                raise ValueError(
                    "Substitute (Domain name) rule type is not applicable for IP Address or "
                    + "Client IP Address object types. See other action Create RPZ A Rule or"
                    + "Create RPZ AAAA Rule actions."
                )
            canonical = substitute_name

        url = self._get_full_url(endpoint_identifier)
        body = {
            **additional_params,
            "canonical": canonical,
            "rp_zone": rp_zone,
            "name": create_rpz_rule_name(name, rp_zone),
            "view": view,
            "comment": comment,
        }

        body = clean_params(body)

        response = self._make_rest_call(endpoint_identifier, "POST", url, body=body)

        return response

    def update_rpz_cname_rule(
        self,
        reference_id: str,
        rule_type: str,
        name: str,
        rp_zone: str,
        comment: Optional[str],
        substitute_name: Optional[str],
        view: Optional[str],
        additional_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update a CNAME RPZ Rule.
        """
        canonical = ""
        if rule_type == "Block (No data)":
            canonical = "*"
        elif rule_type == "Passthru":
            canonical = "rpz-passthru" if ":clientipaddress" in reference_id else name
        elif rule_type == "Block (No such domain)":
            canonical = ""
        elif rule_type == "Substitute (Domain name)":
            if not substitute_name:
                raise ValueError(
                    "Substitute Name is required for Substitute (Domain name) rule type."
                )
            if ":ipaddress" in reference_id or ":clientipaddress" in reference_id:
                raise ValueError(
                    "Substitute (Domain name) rule type is not applicable for IP Address or "
                    + "Client IP Address object types."
                )
            canonical = substitute_name
        if not (":ipaddress" in reference_id or ":clientipaddress" in reference_id):
            name = create_rpz_rule_name(name, rp_zone)
        url = self._get_full_url(UPDATE_RPZ_CNAME_ACTION_IDENTIFIER, reference_id=reference_id)
        body = {
            **additional_params,
            "canonical": canonical,
            "rp_zone": rp_zone,
            "name": name,
            "view": view,
            "comment": comment,
        }

        body = clean_params(body)
        response = self._make_rest_call(UPDATE_RPZ_CNAME_ACTION_IDENTIFIER, "PUT", url, body=body)

        return response

    def create_host_record(
        self,
        name: str,
        ipv4_addresses: Optional[List[Dict[str, Any]]],
        ipv6_addresses: Optional[List[Dict[str, Any]]],
        view: Optional[str],
        comment: Optional[str],
        aliases: Optional[List[str]],
        configure_for_dns: bool,
        extended_attributes: Optional[Dict[str, Any]],
        additional_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a host record in Infoblox.

        Args:
            name (str): The name of the host record.
            ipv4_addresses (list): The IPv4 addresses of the host record.
            ipv6_addresses (list): The IPv6 addresses of the host record.
            view (str): The name of the DNS view.
            comment (str): A comment for the host record.
            aliases (list): A list of aliases for the host record.
            configure_for_dns (bool): Whether to configure the host record for DNS.
            extended_attributes (dict): A dictionary of extended attributes for the host record.
            additional_params (dict): A dictionary of any additional parameters for the host record.

        Returns:
            dict: The API response.
        """
        url = self._get_full_url(CREATE_HOST_RECORD_ACTION_IDENTIFIER)
        body = {
            **additional_params,
            "aliases": aliases,
            "configure_for_dns": configure_for_dns,
            "ipv6addrs": ipv6_addresses,
            "ipv4addrs": ipv4_addresses,
            "name": name,
            "view": view,
            "comment": comment,
        }
        if extended_attributes:
            body.update({"extattrs": parse_extended_attributes_to_dict(extended_attributes)})

        body = clean_params(body)
        response = self._make_rest_call(
            CREATE_HOST_RECORD_ACTION_IDENTIFIER, "POST", url, body=body
        )

        return response
