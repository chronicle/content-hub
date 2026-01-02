from __future__ import annotations
import time
import requests
import urllib.parse

from .datamodels import DNSSecurityEvent, SOCInsight
from .InfobloxExceptions import RateLimitException
from .utils import HandleExceptions, string_to_list, clean_params
from .constants import (
    ENDPOINTS,
    DEFAULT_RESULTS_LIMIT,
    DEFAULT_PAGE_SIZE,
    RETRY_COUNT,
    DEFAULT_REQUEST_TIMEOUT,
    WAIT_TIME_FOR_RETRY,
    RATE_LIMIT_EXCEEDED_STATUS_CODE,
    PING_ACTION_IDENTIFIER,
    TIDE_RLIMIT,
    INDICATOR_THREAT_LOOKUP_WITH_TIDE_ACTION_IDENTIFIER,
    GET_INDICATOR_INTEL_LOOKUP_RESULT_ACTION_IDENTIFIER,
    DEFAULT_OFFSET,
    DEFAULT_LIMIT,
    IP_LOOKUP_ACTION_IDENTIFIER,
    INITIATE_INDICATOR_INTEL_LOOKUP_WITH_DOSSIER_ACTION_IDENTIFIER,
    UPDATE_CUSTOM_LIST_ITEMS_ACTION_IDENTIFIER,
    GET_CUSTOM_LIST_BY_ID_ACTION_IDENTIFIER,
    GET_CUSTOM_LIST_ACTION_IDENTIFIER,
    CREATE_CUSTOM_LIST_ACTION_IDENTIFIER,
    CREATE_NETWORK_LIST_ACTION_IDENTIFIER,
    UPDATE_NETWORK_LIST_ACTION_IDENTIFIER,
    CREATE_SECURITY_POLICY_ACTION_IDENTIFIER,
    UPDATE_SECURITY_POLICY_ACTION_IDENTIFIER,
    REMOVE_SECURITY_POLICY_ACTION_IDENTIFIER,
    GET_SECURITY_POLICIES_ACTION_IDENTIFIER,
    REMOVE_NETWORK_LIST_ACTION_IDENTIFIER,
    REMOVE_CUSTOM_LIST_ACTION_IDENTIFIER,
    GET_SOC_INSIGHTS_COMMENTS_ACTION_IDENTIFIER,
    GET_SOC_INSIGHTS_INDICATORS_ACTION_IDENTIFIER,
    GET_SOC_INSIGHTS_EVENTS_ACTION_IDENTIFIER,
    DNS_RECORD_LOOKUP_ACTION_IDENTIFIER,
    GET_NETWORK_LIST_ACTION_IDENTIFIER,
    DHCP_LEASE_LOOKUP_ACTION_IDENTIFIER,
    GET_SOC_INSIGHTS_ASSETS_ACTION_IDENTIFIER,
    HOST_LOOKUP_ACTION_IDENTIFIER,
    GET_SOC_INSIGHTS_ACTION_IDENTIFIER,
    GET_DNS_SECURITY_EVENTS_ACTION_IDENTIFIER,
)


class APIManager:
    def __init__(self, api_root, api_key, verify_ssl=False, siemplify=None):
        """
        Initializes an object of the APIManager class.

        Args:
            api_root (str): API root of the Infoblox server.
            api_key (str): API key of the Infoblox account.
            verify_ssl (bool, optional): If True, verify the SSL certificate for the connection.
                Defaults to False.
            siemplify (object, optional): An instance of the SDK SiemplifyConnectorExecution class.
                Defaults to None.
        """
        self.api_root = api_root
        self.api_key = api_key
        self.siemplify = siemplify
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers.update(
            {
                "Authorization": f"Token {self.api_key}",
            }
        )

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full URL from URL identifier.

        Args:
            url_id (str): The ID of the URL.
            kwargs (dict): Variables passed for string formatting.

        Returns:
            str: The full URL.
        """
        return urllib.parse.urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def _paginator(
        self,
        api_name,
        method,
        url,
        result_key="results",
        params=None,
        body=None,
        limit=DEFAULT_RESULTS_LIMIT,
        is_connector_request=False,
    ):
        """
        Paginate the results.

        Args:
            api_name (str): API name.
            method (str): The method of the request (GET, POST, PUT, DELETE, PATCH).
            url (str): The URL to send the request to.
            result_key (str, optional): The key to extract data. Defaults to "results".
            params (dict, optional): The parameters of the request.
            body (dict, optional): The JSON payload of the request.
            limit (int, optional): The limit of the results. Defaults to DEFAULT_RESULTS_LIMIT.

        Returns:
            list: List of results.
        """
        limit = limit or DEFAULT_RESULTS_LIMIT
        params["_offset"] = params.get("_offset", 0)
        params["_limit"] = DEFAULT_PAGE_SIZE if limit >= DEFAULT_PAGE_SIZE else limit
        response = self._make_rest_call(api_name, method, url, params=params, body=body)
        results = response.get(result_key, [])

        while True:
            if not response.get(result_key) or len(results) >= limit:
                break
            remaining = limit - len(results)
            params["_offset"] += params["_limit"]
            params["_limit"] = (
                DEFAULT_PAGE_SIZE if remaining >= DEFAULT_PAGE_SIZE else remaining
            )
            if is_connector_request:
                try:
                    response = self._make_rest_call(
                        api_name, method, url, params=params, body=body
                    )
                except Exception as e:
                    self.siemplify.LOGGER.exception(e)
                    return results
            else:
                response = self._make_rest_call(
                    api_name, method, url, params=params, body=body
                )
            results.extend(response.get(result_key, []))

        return results

    def _make_rest_call(
        self,
        api_identifier,
        method,
        url,
        params=None,
        body=None,
        retry_count=RETRY_COUNT,
    ):
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
        response = self.session.request(
            method,
            url,
            params=params,
            json=body,
            timeout=DEFAULT_REQUEST_TIMEOUT,
        )
        try:
            self.validate_response(api_identifier, response)
        except RateLimitException:
            if retry_count > 0:
                time.sleep(WAIT_TIME_FOR_RETRY)
                retry_count -= 1
                return self._make_rest_call(
                    api_identifier, method, url, params, body, retry_count
                )
            else:
                raise RateLimitException("API rate limit exceeded.")

        try:
            return response.json()
        except Exception:
            self.siemplify.LOGGER.error(
                "Exception occurred while returning response JSON for API identifier"
                f"{api_identifier} and URL {url}"
            )
            return {}

    @staticmethod
    def validate_response(api_identifier, response, error_msg="An error occurred"):
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

    def test_connectivity(self):
        """
        Test connectivity to the Infoblox.

        Returns:
            bool: True if successful, exception otherwise.
        """
        request_url = self._get_full_url(PING_ACTION_IDENTIFIER)
        _ = self._make_rest_call(PING_ACTION_IDENTIFIER, "GET", request_url)
        return True

    def indicator_threat_lookup_with_tide(
        self,
        indicator_type=None,
        indicator_value=None,
        domain=None,
        tld=None,
        threat_class=None,
        target=None,
        expiration=None,
        rlimit=TIDE_RLIMIT,
    ):
        """
        Perform Indicator Threat Lookup With TIDE.
        Args:
            indicator_type (str): Indicator type (Host, IP, URL, Email, Hash, All)
            indicator_value (str): Value of the indicator (if not All)
            domain (str): Comma-separated domains
            tld (str): Comma-separated TLDs
            threat_class (str): Comma-separated threat classes
            target (str): Comma-separated targets
            expiration (str): Expiration date (ISO8601)
        Returns:
            dict: API response
        """
        params = {
            "rlimit": rlimit,
            "tld": tld,
            "class": threat_class,
            "target": target,
            "expiration": expiration,
            "domain": domain,
        }

        if indicator_type and indicator_type.lower() != "all":
            params["type"] = indicator_type.lower()
            params[indicator_type.lower()] = indicator_value
        params = clean_params(params)

        url = self._get_full_url(INDICATOR_THREAT_LOOKUP_WITH_TIDE_ACTION_IDENTIFIER)
        return self._make_rest_call(
            INDICATOR_THREAT_LOOKUP_WITH_TIDE_ACTION_IDENTIFIER,
            "GET",
            url,
            params=params,
        )

    def get_indicator_intel_lookup_result(self, job_id):
        """
        Get Indicator Intel Lookup Result (Dossier Job Results).
        Args:
            job_id (str): The Job ID returned from the Initiate Indicator Intel Lookup With
            Dossier action.
        Returns:
            dict: API response
        """
        url = self._get_full_url(
            GET_INDICATOR_INTEL_LOOKUP_RESULT_ACTION_IDENTIFIER, job_id=job_id
        )
        return self._make_rest_call(
            GET_INDICATOR_INTEL_LOOKUP_RESULT_ACTION_IDENTIFIER, "GET", url
        )

    def ip_lookup(
        self,
        ip_filter=None,
        address_state=None,
        scope=None,
        tag_filter=None,
        offset=DEFAULT_OFFSET,
        limit=DEFAULT_LIMIT,
        order_by=None,
    ):
        """
        Retrieve information related to a specific IP address from Infoblox.
        Args:
            ip_filter (str): Filter IP addresses by specific criteria
                (e.g., address=="192.168.1.100" or state=="USED")
            address_state (str): Filter by IP address state (e.g., 'free', 'used')
            scope (str): Specify the scope for IP address lookup
            tag_filter (str): Filter IP addresses by specific tags (e.g. 'Tenable_scan'=='true')
            order_by (str): Field(s) to order results by
        Returns:
            dict: API response
        """
        params = {
            "_tfilter": tag_filter,
            "_filter": ip_filter,
            "address_state": address_state,
            "scope": scope,
            "_offset": offset,
            "_limit": limit,
            "_order_by": order_by,
        }
        params = clean_params(params)

        url = self._get_full_url(IP_LOOKUP_ACTION_IDENTIFIER)
        return self._make_rest_call(
            IP_LOOKUP_ACTION_IDENTIFIER, "GET", url, params=params
        )

    def initiate_indicator_intel_lookup_with_dossier(
        self,
        indicator_type,
        indicator_value,
        source=None,
        wait_for_results=False,
    ):
        """
        Initiate Indicator Intel Lookup With Dossier.
        Args:
            indicator_type (str): The type of indicator (Host, IP, URL, Email, Hash, All)
            indicator_value (str): The value of the indicator
            source (str): Comma-separated sources to query
            wait_for_results (bool): Whether to wait for results
        Returns:
            dict: API response
        """
        source_items = string_to_list(source)
        params = [("value", indicator_value)]
        for source_item in source_items:
            params.append(("source", source_item))
        if wait_for_results:
            params.append(("wait", "true"))
        url = self._get_full_url(
            INITIATE_INDICATOR_INTEL_LOOKUP_WITH_DOSSIER_ACTION_IDENTIFIER,
            type=indicator_type.lower(),
        )
        return self._make_rest_call(
            INITIATE_INDICATOR_INTEL_LOOKUP_WITH_DOSSIER_ACTION_IDENTIFIER,
            "GET",
            url,
            params=params,
        )

    def update_custom_list_items(self, custom_list_id, action, items):
        """
        Add or Remove items in a custom list.

        Args:
            custom_list_id (int): ID of the custom list.
            action (str): 'Add' or 'Remove'.
            items (list): List of items (IPs, domains, networks) to add or remove.
        Returns:
            dict: API response.
        """
        url = self._get_full_url(
            UPDATE_CUSTOM_LIST_ITEMS_ACTION_IDENTIFIER,
            custom_list_id=custom_list_id,
        )
        body = {"deleted_items_described": [], "inserted_items_described": []}
        if action == "Add":
            body["inserted_items_described"] = [
                {"item": item, "description": ""} for item in items
            ]
        else:
            body["deleted_items_described"] = [
                {"item": item, "description": ""} for item in items
            ]
        return self._make_rest_call(
            UPDATE_CUSTOM_LIST_ITEMS_ACTION_IDENTIFIER,
            "PATCH",
            url,
            params=None,
            body=body,
        )

    def get_custom_list(
        self,
        custom_list_id=None,
        name=None,
        type_=None,
        tag_filter=None,
        tag_sort_filter=None,
        offset=DEFAULT_OFFSET,
        limit=DEFAULT_LIMIT,
    ):
        """
        Retrieve custom list(s) from Infoblox.

        Args:
            custom_list_id (int|None): ID of the custom list.
            name (str|None): Name of the custom list.
            type_ (str|None): Type of the custom list.
            tag_filter (str|None): Tag filter.
            tag_sort_filter (str|None): Tag sort filter.
            offset (int): Pagination offset.
            limit (int): Max results.
        Returns:
            dict: API response.
        """
        params = {"_offset": offset, "_limit": limit}
        # If Custom List ID is provided, use /custom_lists/{id}
        if custom_list_id:
            url = self._get_full_url(
                GET_CUSTOM_LIST_BY_ID_ACTION_IDENTIFIER,
                custom_list_id=custom_list_id,
            )
            return self._make_rest_call(
                GET_CUSTOM_LIST_BY_ID_ACTION_IDENTIFIER, "GET", url, params=None
            )
        # If both Name and Type are provided, use /custom_lists/0 with query params
        elif name and type_:
            url = self._get_full_url(
                GET_CUSTOM_LIST_BY_ID_ACTION_IDENTIFIER, custom_list_id=0
            )
            params.update({"name": name, "type": type_})
            return self._make_rest_call(
                GET_CUSTOM_LIST_BY_ID_ACTION_IDENTIFIER,
                "GET",
                url,
                params=params,
            )
        # If only Name or only Type is provided, ignore them and use base endpoint
        else:
            url = self._get_full_url(GET_CUSTOM_LIST_ACTION_IDENTIFIER)
            if tag_filter:
                params["_tfilter"] = tag_filter
            if tag_sort_filter:
                params["_torder_by"] = tag_sort_filter
            return self._make_rest_call(
                GET_CUSTOM_LIST_ACTION_IDENTIFIER, "GET", url, params=params
            )

    def create_custom_list(self, payload):
        """
        Create a new custom list in Infoblox.

        Args:
            payload (dict): The request body for the custom list.
        Returns:
            dict: API response.
        """
        url = self._get_full_url(CREATE_CUSTOM_LIST_ACTION_IDENTIFIER)
        response = self._make_rest_call(
            CREATE_CUSTOM_LIST_ACTION_IDENTIFIER,
            "POST",
            url,
            params=None,
            body=payload,
        )
        return response

    def create_network_list(self, name, items, description=None):
        """
        Create a new network list in Infoblox.

        Args:
            name (str): Name of the network list (must be unique).
            items (list): List of items (IP addresses, CIDRs).
            description (str|None): Description for the network list.
        Returns:
            dict: API response.
        """
        url = self._get_full_url(CREATE_NETWORK_LIST_ACTION_IDENTIFIER)
        body = {"name": name, "items": items}
        if description:
            body["description"] = description
        response = self._make_rest_call(
            CREATE_NETWORK_LIST_ACTION_IDENTIFIER,
            "POST",
            url,
            params=None,
            body=body,
        )
        return response

    def update_network_list(
        self, network_list_id, name=None, items=None, description=None
    ):
        """
        Update an existing network list in Infoblox. Fields left empty are 
            fetched from current data.
        Args:
            network_list_id (str): ID of the network list to update
                (should be string for consistency).
            name (str|None): New name for the network list.
            items (list|None): New list of items (CIDRs). None means keep existing;
            description (str|None): New description. None means keep existing;
        Returns:
            dict: API response.
        """
        # Fetch current data using get_network_list (should return a dict for the specified ID)
        current_data = self.get_network_list(network_list_id=network_list_id)
        current_data = current_data.get("results")

        # Build body
        fields = {"name": name, "items": items, "description": description}
        body = {}
        for key, value in fields.items():
            if not value:
                body[key] = current_data.get(key)
            elif (
                isinstance(value, str)
                and value.strip().lower() == "empty"
                and key == "description"
            ):
                body[key] = ""
            else:
                body[key] = value

        update_url = self._get_full_url(
            UPDATE_NETWORK_LIST_ACTION_IDENTIFIER,
            network_list_id=network_list_id,
        )
        response = self._make_rest_call(
            UPDATE_NETWORK_LIST_ACTION_IDENTIFIER,
            "PUT",
            update_url,
            params=None,
            body=body,
        )
        return response

    def create_security_policy(self, payload):
        """
        Create a new security policy in Infoblox.
        Args:
            payload (dict): The request body for the security policy.
        Returns:
            dict: API response.
        """
        url = self._get_full_url(CREATE_SECURITY_POLICY_ACTION_IDENTIFIER)
        response = self._make_rest_call(
            CREATE_SECURITY_POLICY_ACTION_IDENTIFIER, "POST", url, body=payload
        )
        return response

    def update_security_policy(self, security_policy_id, payload):
        """
        Update an existing security policy in Infoblox.

        Args:
            security_policy_id (int): The ID of the security policy to update.
            payload (dict): The request body for the update.
        Returns:
            dict: API response.
        """
        url = self._get_full_url(
            UPDATE_SECURITY_POLICY_ACTION_IDENTIFIER,
            security_policy_id=security_policy_id,
        )
        response = self._make_rest_call(
            UPDATE_SECURITY_POLICY_ACTION_IDENTIFIER, "PUT", url, body=payload
        )
        return response

    def remove_security_policy(self, security_policy_id):
        """
        Remove a security policy by ID in Infoblox.

        Args:
            security_policy_id (int): The ID of the security policy to remove.
        Returns:
            dict: API response (empty on success).
        Raises:
        """
        url = self._get_full_url(
            REMOVE_SECURITY_POLICY_ACTION_IDENTIFIER,
            security_policy_id=security_policy_id,
        )
        response = self._make_rest_call(
            REMOVE_SECURITY_POLICY_ACTION_IDENTIFIER, "DELETE", url
        )
        return response

    def get_security_policies(
        self,
        security_policy_filter=None,
        tag_filter=None,
        tag_sort_filter=None,
        offset=DEFAULT_OFFSET,
        limit=DEFAULT_LIMIT,
    ):
        """
        Retrieve security policies from Infoblox.
        Args:
            security_policy_filter (str): Logical filter string for policies.
            tag_filter (str): Filter by tags.
            tag_sort_filter (str): Sort by tags.
            offset (int): Pagination offset.
            limit (int): Max results.
        Returns:
            dict: API response.
        """
        params = {
            "_offset": offset,
            "_limit": limit,
            "_tfilter": tag_filter,
            "_filter": security_policy_filter,
            "_torder_by": tag_sort_filter,
        }
        params = clean_params(params)
        url = self._get_full_url(GET_SECURITY_POLICIES_ACTION_IDENTIFIER)
        return self._make_rest_call(
            GET_SECURITY_POLICIES_ACTION_IDENTIFIER, "GET", url, params=params
        )

    def remove_network_list(self, network_list_id):
        """
        Args:
            network_list_id (str|int): ID of the network list to remove.
        Returns:
            dict: API response (usually empty on success).
        Raises:
            Exception: If the network list does not exist or is assigned to a security policy.
        """
        url = self._get_full_url(
            REMOVE_NETWORK_LIST_ACTION_IDENTIFIER,
            network_list_id=network_list_id,
        )
        response = self._make_rest_call(
            REMOVE_NETWORK_LIST_ACTION_IDENTIFIER, "DELETE", url
        )
        return response

    def remove_custom_list(self, custom_list_id):
        """
        Remove a custom list by ID.
        Args:
            custom_list_id (int): The ID of the custom list to remove.
        Returns:
            dict: API response (usually empty on success).
        """
        url = self._get_full_url(
            REMOVE_CUSTOM_LIST_ACTION_IDENTIFIER, custom_list_id=custom_list_id
        )
        return self._make_rest_call(REMOVE_CUSTOM_LIST_ACTION_IDENTIFIER, "DELETE", url)

    def update_custom_list(self, custom_list_id, payload):
        """
        Update a custom list by ID.
        Args:
            custom_list_id (int): The ID of the custom list to update.
            payload (dict): The request body for the update.
        Returns:
            dict: API response.
        Raises:
            InfobloxException: For API or validation errors.
        """
        url = self._get_full_url(
            GET_CUSTOM_LIST_BY_ID_ACTION_IDENTIFIER,
            custom_list_id=custom_list_id,
        )
        return self._make_rest_call(
            GET_CUSTOM_LIST_BY_ID_ACTION_IDENTIFIER,
            "PUT",
            url,
            params=None,
            body=payload,
        )

    def get_soc_insights_comments(self, insight_id, from_time=None, to_time=None):
        """
        Retrieve comments for a given SOC Insight.
        Args:
            insight_id (str): ID of the insight (required)
            from_time (str|None): Filter comments changed after this time (optional)
            to_time (str|None): Filter comments changed before this time (optional)
        Returns:
            dict: API response
        """
        url = self._get_full_url(
            GET_SOC_INSIGHTS_COMMENTS_ACTION_IDENTIFIER, insight_id=insight_id
        )
        params = {}
        if from_time:
            params["from"] = from_time
        if to_time:
            params["to"] = to_time
        return self._make_rest_call(
            GET_SOC_INSIGHTS_COMMENTS_ACTION_IDENTIFIER,
            "GET",
            url,
            params=params,
        )

    def get_soc_insights_indicators(
        self,
        insight_id,
        confidence=None,
        indicator=None,
        actor=None,
        from_time=None,
        to_time=None,
        action=None,
        limit=DEFAULT_LIMIT,
    ):
        """
        Retrieve indicators for a given SOC Insight.
        Args:
            insight_id (str): ID of the insight (required)
            confidence (str|None): Filter by confidence score (optional)
            indicator (str|None): Filter by specific indicator value (optional)
            actor (str|None): Filter by threat actor (optional)
            from_time (str|None): Filter indicators seen after this time (optional)
            to_time (str|None): Filter indicators seen before this time (optional)
        Returns:
            dict: API response
        """
        url = self._get_full_url(
            GET_SOC_INSIGHTS_INDICATORS_ACTION_IDENTIFIER, insight_id=insight_id
        )
        params = {
            "confidence": confidence,
            "indicator": indicator,
            "actor": actor,
            "action": action,
            "from": from_time,
            "to": to_time,
            "limit": limit,
        }
        params = clean_params(params)
        return self._make_rest_call(
            GET_SOC_INSIGHTS_INDICATORS_ACTION_IDENTIFIER,
            "GET",
            url,
            params=params,
        )

    def get_soc_insights_events(
        self,
        insight_id,
        device_ip=None,
        query=None,
        query_type=None,
        source=None,
        indicator=None,
        threat_level=None,
        confidence_level=None,
        limit=None,
        from_time=None,
        to_time=None,
    ):
        """
        Retrieve SOC Insight events for a given insight ID with optional filters.
        Args:
            insight_id (str): ID of the insight (required)
            device_ip (str|None): Filter by Device IP
            query (str|None): Filter by query string
            query_type (str|None): Filter by DNS query type
            source (str|None): Filter by threat intelligence source/feed
            indicator (str|None): Filter by threat indicator
            threat_level (str|None): Filter by threat level
            confidence_level (str|None): Filter by confidence level
            limit (int|None): Max results to return
            from_time (str|None): Filter by events detected after this time
            to_time (str|None): Filter by events detected before this time
        Returns:
            dict: API response
        """
        url = self._get_full_url(
            GET_SOC_INSIGHTS_EVENTS_ACTION_IDENTIFIER, insight_id=insight_id
        )
        params = {
            "device_ip": device_ip,
            "query": query,
            "query_type": query_type,
            "source": source,
            "indicator": indicator,
            "threat_level": (
                threat_level if threat_level and threat_level.lower() != "all" else None
            ),
            "confidence_level": (
                confidence_level
                if confidence_level and confidence_level.lower() != "all"
                else None
            ),
            "limit": limit,
            "from": from_time,
            "to": to_time,
        }
        # Remove any keys where value is None
        params = clean_params(params)
        return self._make_rest_call(
            GET_SOC_INSIGHTS_EVENTS_ACTION_IDENTIFIER, "GET", url, params=params
        )

    def dns_record_lookup(
        self,
        dns_record_filter=None,
        tag_filter=None,
        offset=DEFAULT_OFFSET,
        limit=DEFAULT_LIMIT,
        order_by=None,
    ):
        """
        Retrieve DNS records from Infoblox.

        Args:
            dns_record_filter (str): Logical expression string for DNS record filtering.
            tag_filter (str): Logical expression string for tag filtering.
            offset (int): Pagination offset.
            limit (int): Maximum number of results to return.
            order_by (str): Field(s) to order results by.

        Returns:
            dict: API response containing DNS records.
        """
        url = self._get_full_url(DNS_RECORD_LOOKUP_ACTION_IDENTIFIER)
        params = {
            "_offset": offset,
            "_limit": limit,
            "_filter": dns_record_filter,
            "_tfilter": tag_filter,
            "_order_by": order_by,
        }
        params = clean_params(params)
        response = self._make_rest_call(
            DNS_RECORD_LOOKUP_ACTION_IDENTIFIER, "GET", url, params=params
        )
        return response

    def get_network_list(
        self,
        network_filter=None,
        network_list_id=None,
        offset=DEFAULT_OFFSET,
        limit=DEFAULT_LIMIT,
    ):
        """
        Retrieve network lists from Infoblox.

        Args:
            network_filter (str): Logical expression string to filter results.
            network_list_id (str|int|None): If provided, only this ID is used as a filter and all
                other filters are ignored.
            offset (int): Pagination offset.
            limit (int): Maximum number of results to return.

        Returns:
            list: List of network lists (dicts).
        """

        params = {"_limit": limit, "_offset": offset}
        if network_filter:
            params["_filter"] = network_filter
        url = self._get_full_url(GET_NETWORK_LIST_ACTION_IDENTIFIER)
        if network_list_id:
            url = url + f"/{network_list_id}"
            params = {}

        response = self._make_rest_call(
            GET_NETWORK_LIST_ACTION_IDENTIFIER, "GET", url, params=params
        )
        return response

    def get_dhcp_lease_lookup(
        self,
        dhcp_lease_filter=None,
        offset=DEFAULT_OFFSET,
        limit=DEFAULT_LIMIT,
        order_by=None,
    ):
        """
        Look up DHCP lease information for a given IP or MAC address or filter.

        Args:
            dhcp_lease_filter (str, optional): Filter DHCP leases by specific criteria
                (e.g., address=="127.0.0.1" and hostname=="ubuntu").
            offset (int, optional): Pagination offset (default: 0).
            limit (int, optional): Maximum number of results to return (default: 100).
            order_by (str, optional): Field(s) to order results by.

        Returns:
            dict: API response containing DHCP lease records.
        """
        url = self._get_full_url(DHCP_LEASE_LOOKUP_ACTION_IDENTIFIER)
        params = {
            "_offset": offset,
            "_limit": limit,
            "_filter": dhcp_lease_filter,
            "_order_by": order_by,
        }
        params = clean_params(params)
        return self._make_rest_call(
            DHCP_LEASE_LOOKUP_ACTION_IDENTIFIER, "GET", url, params=params
        )

    def get_soc_insights_assets(
        self,
        insight_id,
        asset_ip=None,
        mac_address=None,
        os_version=None,
        user=None,
        limit=DEFAULT_LIMIT,
        from_time=None,
        to_time=None,
    ):
        """
        Retrieve the list of associated assets for a given Insight ID.

        Args:
            insight_id (str): The ID of the insight to retrieve assets from (required)
            asset_ip (str, optional): Filter assets by IP address
            mac_address (str, optional): Filter assets by MAC address
            os_version (str, optional): Filter assets by operating system version
            user (str, optional): Filter assets by associated user
            limit (int, optional): Maximum number of results to return (default: 100)
            from_time (str, optional): Filter by assets changed after this time
                (YYYY-MM-DDTHH:mm:ss.SSS)
            to_time (str, optional): Filter by assets changed before this time
                (YYYY-MM-DDTHH:mm:ss.SSS)

        Returns:
            dict: API response
        Raises:
            ItemNotFoundException: If the insight_id does not exist (404)
        """
        url = self._get_full_url(
            GET_SOC_INSIGHTS_ASSETS_ACTION_IDENTIFIER, insight_id=insight_id
        )
        params = {
            "qip": asset_ip,
            "cmac": mac_address,
            "os_version": os_version,
            "user": user,
            "limit": limit,
            "from": from_time,
            "to": to_time,
        }
        # Remove any keys where value is None
        params = clean_params(params)
        return self._make_rest_call(
            GET_SOC_INSIGHTS_ASSETS_ACTION_IDENTIFIER, "GET", url, params=params
        )

    def get_host_lookup(
        self,
        host_filter=None,
        tag_filter=None,
        offset=DEFAULT_OFFSET,
        limit=DEFAULT_LIMIT,
        order_by=None,
    ):
        """
        Retrieve host information from Infoblox with optional filters.

        Args:
            host_filter (str, optional): Filter IPAM hosts by specific criteria
                (e.g., name=="webserver01" or ip_address=="192.168.1.100").
            tag_filter (str, optional): Filter IP addresses by specific tags 
                (e.g. 'Tenable_scan'=='true').
            offset (int, optional): Pagination offset (default: 0).
            limit (int, optional): Maximum number of results to return (default: 100).
            order_by (str, optional): Field(s) to order results by.

        Returns:
            dict: API response containing host asset records.
        """
        url = self._get_full_url(HOST_LOOKUP_ACTION_IDENTIFIER)
        params = {
            "_offset": offset,
            "_limit": limit,
            "_filter": host_filter,
            "_tfilter": tag_filter,
            "_order_by": order_by,
        }
        params = clean_params(params)
        return self._make_rest_call(
            HOST_LOOKUP_ACTION_IDENTIFIER, "GET", url, params=params
        )

    def get_soc_insights(
        self, existing_ids=None, status=None, threat_type=None, priority=None
    ):
        """
        Retrieve SOC Insights from Infoblox.

        Args:
            existing_ids (list, optional): List of already processed insights IDs to filter out
            status (str, optional): Filter insights by status (e.g., "Active", "Closed")
            threat_type (str, optional): Filter insights by threat type
            priority (str, optional): Filter insights by priority level 
                (LOW, INFO, MEDIUM, HIGH, CRITICAL)

        Returns:
            list: List of SOC Insight objects
        """

        params = {
            "status": status,
            "threat_type": threat_type,
            "priority": priority,
        }

        params = clean_params(params)

        url = self._get_full_url(GET_SOC_INSIGHTS_ACTION_IDENTIFIER)
        response = self._make_rest_call(
            GET_SOC_INSIGHTS_ACTION_IDENTIFIER, "GET", url, params=params
        )

        # Extract insights from response
        insights = []
        if response and "insightList" in response:
            insights = [
                insight
                for item in response["insightList"]
                if (insight := SOCInsight(item)).event_id not in existing_ids
            ]

        return insights

    def get_dns_security_events(self, existing_ids=None, **kwargs):
        """
        Retrieve DNS Security Events from Infoblox and filter out already processed events.

        Args:
            existing_ids (list, optional): List of already processed event IDs to filter out
            t0 (str, optional): Start timestamp in epoch seconds or ISO format
                (YYYY-MM-DDThh:mm:ss.sssZ)
            t1 (str, optional): End timestamp in epoch seconds or ISO format
                (YYYY-MM-DDThh:mm:ss.sssZ)
            queried_name (str, optional): Filter by comma-separated queried domain names
            policy_name (str, optional): Filter by comma-separated security policy names
            threat_level (str, optional): Filter by threat severity level (LOW, MEDIUM, HIGH)
            threat_class (str, optional): Filter by comma-separated threat category
            threat_family (str, optional): Filter by comma-separated threat family
            threat_indicator (str, optional): Filter by comma-separated threat indicators
            policy_action (str, optional): Filter by comma-separated action performed
            feed_name (str, optional): Filter by comma-separated threat feed or custom list name
            network (str, optional): Filter by comma-separated network name
            limit (int, optional): Maximum number of results to return (default: 1000)

        Returns:
            tuple: (list of DNS Security Event objects, list of DNSSecurityEvent model instances)
        """
        # Build API parameters
        params = self.build_dns_security_events_params(**kwargs)

        # Make API call
        url = self._get_full_url(GET_DNS_SECURITY_EVENTS_ACTION_IDENTIFIER)
        results = self._paginator(
            GET_DNS_SECURITY_EVENTS_ACTION_IDENTIFIER,
            "GET",
            url,
            limit=kwargs.get("limit"),
            params=params,
            is_connector_request=True,
            result_key="result",
        )

        dns_events = [
            event_obj
            for event in results
            if (event_obj := DNSSecurityEvent(event)).event_id not in existing_ids
        ]

        return dns_events

    def build_dns_security_events_params(
        self,
        t0=None,
        t1=None,
        queried_name=None,
        policy_name=None,
        threat_level=None,
        threat_class=None,
        threat_family=None,
        threat_indicator=None,
        policy_action=None,
        feed_name=None,
        network=None,
        **kwargs,
    ):
        """
        Build parameters for DNS Security Events API call.

        Args:
            t0 (str, optional): Start timestamp in epoch seconds or ISO format
            t1 (str, optional): End timestamp in epoch seconds or ISO format
            queried_name (str, optional): Filter by comma-separated queried domain names
            policy_name (str, optional): Filter by comma-separated security policy names
            threat_level (str, optional): Filter by threat severity level
            threat_class (str, optional): Filter by comma-separated threat category
            threat_family (str, optional): Filter by comma-separated threat family
            threat_indicator (str, optional): Filter by comma-separated threat indicators
            policy_action (str, optional): Filter by comma-separated action performed
            feed_name (str, optional): Filter by comma-separated threat feed or custom list name
            network (str, optional): Filter by comma-separated network name
            limit (int, optional): Maximum number of results to return

        Returns:
            dict: Processed parameters dictionary with all None values removed
        """
        # Process list parameters
        list_params = {
            "qname": self._process_list_param(queried_name),
            "policy_name": self._process_list_param(policy_name),
            "threat_class": self._process_list_param(threat_class),
            "threat_family": self._process_list_param(threat_family),
            "threat_indicator": self._process_list_param(threat_indicator),
            "policy_action": self._process_list_param(policy_action),
            "feed_name": self._process_list_param(feed_name),
            "network": self._process_list_param(network),
        }

        # Add scalar parameters
        params = {"t0": t0, "t1": t1, "threat_level": threat_level}

        # Merge dictionaries
        params.update(list_params)

        # Clean params (remove None values)
        return clean_params(params)

    @staticmethod
    def _process_list_param(param):
        """
        Process a comma-separated string parameter into a comma-joined string for API.

        Args:
            param (str): Comma-separated string parameter

        Returns:
            str: Comma-joined string or None if the input was empty
        """
        if not param:
            return None

        return ", ".join(string_to_list(param))
