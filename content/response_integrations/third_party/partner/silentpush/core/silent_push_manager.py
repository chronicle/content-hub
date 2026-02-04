import ipaddress
import json
from typing import Any
from urllib.parse import urlencode

import requests

from .exceptions import SilentPushExceptions

""" CONSTANTS """

DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
RESOURCE = {"ipv4", "ipv6", "domain"}
CONTENT_TYPE = "application/json"

# API ENDPOINT
JOB_STATUS = "explore/job"
NAMESERVER_REPUTATION = "explore/nsreputation/history/nameserver"
SUBNET_REPUTATION = "explore/ipreputation/history/subnet"
ASNS_DOMAIN = "explore/padns/lookup/domain/asns"
DENSITY_LOOKUP = "explore/padns/lookup/density"
SEARCH_DOMAIN = "explore/domain/search"
DOMAIN_INFRATAGS = "explore/bulk/domain/infratags"
DOMAIN_INFO = "explore/bulk/domaininfo"
RISK_SCORE = "explore/bulk/domain/riskscore"
WHOIS = "explore/domain/whois"
DOMAIN_CERTIFICATE = "explore/domain/certificates"
ENRICHMENT = "explore/enrich"
LIST_IP = "explore/bulk/ip2asn"
ASN_REPUTATION = "explore/ipreputation/history/asn"
ASN_TAKEDOWN_REPUTATION = "explore/takedownreputation/asn"
IPV4_REPUTATION = "explore/ipreputation/history/ipv4"
FORWARD_PADNS = "explore/padns/lookup/query"
REVERSE_PADNS = "explore/padns/lookup/answer"
SEARCH_SCAN = "explore/scandata/search/raw"
LIVE_SCAN_URL = "explore/tools/scanondemand"
FUTURE_ATTACK_INDICATOR = "/api/v2/iocs/threat-ranking"
SCREENSHOT_URL = "explore/tools/scanondemand"
ADD_FEED = "/api/v1/feeds/"
EXPORT_DATA = "/app/v1/export/organization-exports/"
THREAT_CHECK = "https://api.threatcheck.silentpush.com/v1/"
MERGE_API = "/api/v1/merge-api"


class SilentPushManager:
    def __init__(self, base_url, api_key, logger=None):
        """
        Initializes the SilentPushManager with API credentials and optional logger.

        Args:
            base_url (str): The base URL/domain of the Silent Push platform.
            api_key (str): The api key used to access Silent Push APIs.
            logger (logging.Logger, optional): Logger instance for logging errors and info.
        """
        full_base_url = base_url.rstrip("/") + MERGE_API

        self.base_url = full_base_url
        self._api_key = api_key
        self.logger = logger
        self._headers = {"X-API-Key": api_key, "Content-Type": CONTENT_TYPE}

    def _http_request(  # type: ignore[override]
        self,
        method: str,
        url_suffix: str = "",
        params: dict = None,
        data: dict = None,
        url: str = None,
        **kwargs,
    ) -> Any:
        """
        Perform an HTTP request to the SilentPush API.

        Args:
            method (str): The HTTP method to use (e.g., 'GET', 'POST').
            url_suffix (str): The endpoint suffix to append to the base URL.
            params (dict, optional): Query parameters to include in the request.
            data (dict, optional): JSON data to send in the request body.

        Returns:
            Any: Parsed JSON response from the API.

        Raises:
            Exception: If the response is not JSON or if the request fails.
        """
        # Properly build the full URL using override if provided
        full_url = (
            url if url else f"{self.base_url.rstrip('/')}/{url_suffix.lstrip('/')}"
        )

        try:
            response = requests.request(
                method=method,
                url=full_url,
                headers=self._headers,
                params=params,
                json=data,
            )
        except requests.exceptions.RequestException as e:
            raise SilentPushExceptions(f"Connection error: {str(e)}")

        # Check for non-2xx HTTP responses
        if not response.ok:
            raise SilentPushExceptions(
                f"HTTP {response.status_code} Error: {response.text}", res=response
            )

        # Try parsing JSON
        try:
            return response.json()
        except ValueError:
            raise SilentPushExceptions("Failed to parse JSON response.", res=response)

    def search_domains(
        self,
        query: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        risk_score_min: int | None = None,
        risk_score_max: int | None = None,
        limit: int | None = 100,
        domain_regex: str | None = None,
        name_server: str | None = None,
        asnum: int | None = None,
        asname: str | None = None,
        min_ip_diversity: int | None = None,
        registrar: str | None = None,
        min_asn_diversity: int | None = None,
        certificate_issuer: str | None = None,
        whois_date_after: str | None = None,
        skip: int | None = None,
    ) -> dict:
        """
        Search for domains based on various filtering criteria.

        Args:
            query (str): Domain search query.
            start_date (str, optional): Start date for domain search (YYYY-MM-DD).
            end_date (str, optional): End date for domain search (YYYY-MM-DD).
            risk_score_min (int, optional): Minimum risk score filter.
            risk_score_max (int, optional): Maximum risk score filter.
            limit (int): Maximum number of results to return (defaults to 100).
            domain_regex (str, optional): Regular expression to filter domains.
            name_server (str, optional): Name server filter.
            asnum (int, optional): Autonomous System Number (ASN) filter.
            asname (str, optional): ASN Name filter.
            min_ip_diversity (int, optional): Minimum IP diversity filter.
            registrar (str, optional): Domain registrar filter.
            min_asn_diversity (int, optional): Minimum ASN diversity filter.
            certificate_issuer (str, optional): Filter domains by certificate issuer.
            whois_date_after (str, optional): Filter domains based on WHOIS date (YYYY-MM-DD).
            skip (int, optional): Number of results to skip.

        Returns:
            dict: Search results matching the specified criteria.
        """
        url_suffix = SEARCH_DOMAIN

        # Prepare parameters and filter out None values using remove_nulls_from_dictionary function
        params = {
            "domain": query,
            "start_date": start_date,
            "end_date": end_date,
            "risk_score_min": risk_score_min,
            "risk_score_max": risk_score_max,
            "limit": limit,
            "domain_regex": domain_regex,
            "name_server": name_server,
            "asnum": asnum,
            "asname": asname,
            "min_ip_diversity": min_ip_diversity,
            "registrar": registrar,
            "asn_diversity_min": min_asn_diversity,
            "cert_issuer": certificate_issuer,
            "whois_date_after": whois_date_after,
            "skip": skip,
        }
        filter_params: dict = {
            key: value for key, value in params.items() if value is not None
        }

        # Make the request with the filtered parameters
        return self._http_request("GET", url_suffix, params=filter_params)

    def get_job_status(self, job_id: str, params: dict) -> dict[str, Any]:
        """
        Retrieve the status of a specific job.

        Args:
            job_id (str): The unique identifier of the job to check.
            params (dict, optional): Optional parameters to include in the request (max_wait, etc.).

        Returns:
            Dict[str, Any]: Job status information.

        Raises:
            ValueError: If max_wait is invalid.
        """
        url_suffix = f"{JOB_STATUS}/{job_id}"
        max_wait = params.get("max_wait", 20)  # type ignore

        if max_wait is not None and not (0 <= max_wait <= 25):
            raise ValueError("max_wait must be an integer between 0 and 25")

        return self._http_request(method="GET", url_suffix=url_suffix, params=params)

    def get_nameserver_reputation(
        self, nameserver: str, explain: bool = False, limit: int = None
    ):
        """
        Retrieve historical reputation data for the specified nameserver.

        Args:
            nameserver (str): The nameserver for which the reputation data is to be fetched.
            explain (bool): Whether to include detailed calculation explanations.
            limit (int): Maximum number of reputation entries to return.

        Returns:
            list: A list of reputation entries (each being a dict) for the given nameserver.
        """
        url_suffix = f"{NAMESERVER_REPUTATION}/{nameserver}"

        params = {"explain": int(bool(explain)), "limit": limit}

        filter_params: dict = {
            key: value for key, value in params.items() if value is not None
        }

        response = self._http_request(
            method="GET", url_suffix=url_suffix, params=filter_params
        )

        if isinstance(response, str):
            try:
                response = json.loads(response)
            except Exception as e:
                raise ValueError(f"Unable to parse JSON from response: {e}")

        return response.get("response", {}).get("ns_server_reputation_history", [])

    def get_subnet_reputation(
        self, subnet: str, explain: bool = False, limit: int | None = None
    ) -> dict[str, Any]:
        """
        Retrieve reputation history for a specific subnet.

        Args:
            subnet (str): The subnet to query.
            explain (bool, optional): Whether to include detailed explanations. Defaults to False.
            limit (int, optional): Maximum number of results to return. Defaults to None.

        Returns:
            Dict[str, Any]: Subnet reputation history information.
        """
        url_suffix = f"{SUBNET_REPUTATION}/{subnet}"

        params = {"explain": str(explain).lower() if explain else None, "limit": limit}
        filter_params: dict = {
            key: value for key, value in params.items() if value is not None
        }

        return self._http_request(
            method="GET", url_suffix=url_suffix, params=filter_params
        )

    def get_asns_for_domain(self, domain: str) -> dict[str, Any]:
        """
        Retrieve Autonomous System Numbers (ASNs) associated with the specified domain.

        Args:
            domain (str): The domain to retrieve ASNs for.

        Returns:
            Dict[str, Any]: A dictionary containing the ASN information for the domain.
        """
        url_suffix = f"{ASNS_DOMAIN}/{domain}"

        # Send the request and return the response directly
        return self._http_request(method="GET", url_suffix=url_suffix)

    def density_lookup(self, qtype: str, query: str, **kwargs) -> dict[str, Any]:
        """
        Perform a density lookup based on various query types and
        optional parameters.

        Args:
            qtype (str): Query type to perform the lookup. Options
                include: nssrv, mxsrv, nshash, mxhash, ipv4, ipv6,
                asn, chv.
            query (str): The value to look up.
            **kwargs: Optional parameters (e.g., filters) for
                scoping the lookup.

        Returns:
            Dict[str, Any]: The results of the density lookup,
                containing relevant information based on the query.
        """
        url_suffix = f"{DENSITY_LOOKUP}/{qtype}/{query}"

        params = kwargs
        filter_params: dict = {
            key: value for key, value in params.items() if value is not None
        }

        return self._http_request(
            method="GET", url_suffix=url_suffix, params=filter_params
        )

    def list_domain_infratags(
        self,
        domains: list,
        cluster: bool = False,
        mode: str = "live",
        arg_match: str = "self",
        as_of: str | None = None,
        origin_uid: str | None = None,
    ) -> dict:
        """
        Retrieve infrastructure tags for specified domains, supporting both GET and POST methods.

        Args:
            domains (list): List of domains to fetch infrastructure tags for.
            cluster (bool): Whether to include cluster information (default: False).
            mode (str): Tag retrieval mode (default: 'live').
            match (str): Matching criteria (default: 'self').
            as_of (Optional[str]): Specific timestamp for tag retrieval.
            origin_uid (Optional[str]): Unique identifier for the API user.

        Returns:
            dict: API response containing infratags and optional tag clusters.
        """
        url_suffix = DOMAIN_INFRATAGS

        params = {
            "mode": mode,
            "clusters": int(cluster),
        }

        payload = {
            "domains": domains,
            "match": arg_match,
            "as_of": as_of,
            "origin_uid": origin_uid,
        }
        filter_payload: dict = {
            key: value for key, value in payload.items() if value is not None
        }

        return self._http_request(
            method="POST", url_suffix=url_suffix, data=filter_payload, params=params
        )

    def fetch_bulk_domain_info(self, domains: list[str]) -> dict[str, Any]:
        """Fetch basic domain information for a list of domains."""
        response = self._http_request(
            method="POST", url_suffix=DOMAIN_INFO, data={"domains": domains}
        )
        domain_info_list = response.get("response", {}).get("domaininfo", [])
        return {item["domain"]: item for item in domain_info_list}

    def fetch_risk_scores(self, domains: list[str]) -> dict[str, Any]:
        """Fetch risk scores for a list of domains."""
        response = self._http_request(
            method="POST", url_suffix=RISK_SCORE, data={"domains": domains}
        )
        risk_score_list = response.get("response", [])
        return {item["domain"]: item for item in risk_score_list}

    def fetch_whois_info(self, domain: str) -> dict[str, Any]:
        """Fetch WHOIS information for a single domain."""
        try:
            response = self._http_request(method="GET", url_suffix=f"{WHOIS}/{domain}")
            whois_data = response.get("response", {}).get("whois", [{}])[0]

            return {
                "Registrant Name": whois_data.get("name", "N/A"),
                "Registrant Organization": whois_data.get("org", "N/A"),
                "Registrant Address": (
                    ", ".join(whois_data.get("address", []))
                    if isinstance(whois_data.get("address"), list)
                    else whois_data.get("address", "N/A")
                ),
                "Registrant City": whois_data.get("city", "N/A"),
                "Registrant State": whois_data.get("state", "N/A"),
                "Registrant Country": whois_data.get("country", "N/A"),
                "Registrant Zipcode": whois_data.get("zipcode", "N/A"),
                "Creation Date": whois_data.get("created", "N/A"),
                "Updated Date": whois_data.get("updated", "N/A"),
                "Expiration Date": whois_data.get("expires", "N/A"),
                "Registrar": whois_data.get("registrar", "N/A"),
                "WHOIS Server": whois_data.get("whois_server", "N/A"),
                "Nameservers": ", ".join(whois_data.get("nameservers", [])),
                "Emails": ", ".join(whois_data.get("emails", [])),
            }
        except Exception as e:
            return {"error": str(e)}

    def list_domain_information(
        self,
        domains: list[str],
        fetch_risk_score: bool | None = False,
        fetch_whois_info: bool | None = False,
    ) -> dict[str, Any]:
        """
        Retrieve domain information along with optional risk scores
        and WHOIS data.

        Args:
            domains (List[str]): List of domains to get information
                for.
            fetch_risk_score (bool, optional): Whether to fetch
                risk scores. Defaults to False.
            fetch_whois_info (bool, optional): Whether to fetch
                WHOIS information. Defaults to False.

        Returns:
            Dict[str, Any]: Dictionary containing domain
                information with optional risk scores and WHOIS data.

        Raises:
            ValueError: If more than 100 domains are provided.
        """
        if len(domains) > 100:
            raise ValueError(
                "Maximum of 100 domains can be submitted in a single request."
            )

        domain_info_dict = self.fetch_bulk_domain_info(domains)

        risk_score_dict = self.fetch_risk_scores(domains) if fetch_risk_score else {}

        whois_info_dict = (
            {domain: self.fetch_whois_info(domain) for domain in domains}
            if fetch_whois_info
            else {}
        )

        results = []
        for domain in domains:
            domain_info = {
                "domain": domain,
                **domain_info_dict.get(domain, {}),
            }

            if fetch_risk_score:
                risk_data = risk_score_dict.get(domain, {})
                domain_info.update(
                    {
                        "risk_score": risk_data.get("sp_risk_score", "N/A"),
                        "risk_score_explanation": risk_data.get(
                            "sp_risk_score_explain", "N/A"
                        ),
                    }
                )

            if fetch_whois_info:
                domain_info["whois_info"] = whois_info_dict.get(domain, {})  # type: ignore

            results.append(domain_info)

        return {"domains": results}

    def get_domain_certificates(self, domain: str, **kwargs) -> dict[str, Any]:
        """
        Retrieve SSL certificate details associated with a given domain.

        Args:
            domain (str): The domain for which SSL certificate details are retrieved.
            **kwargs: Optional query parameters for filtering the results.

        Returns:
            Dict[str, Any]: SSL certificate details for the specified domain.
        """
        url_suffix = f"{DOMAIN_CERTIFICATE}/{domain}"
        params = kwargs

        return self._http_request(method="GET", url_suffix=url_suffix, params=params)

    def test_connection(self):
        """
        Tests the connection to the Silent Push API.

        Returns:
            str: "ok" if connection is successful.

        Raises:
            SilentPushExceptions: If the connection fails.
        """
        try:
            resp = self.search_domains(limit=1)

            if isinstance(resp, dict):
                if "errors" in resp or "error" in resp:
                    error_msg = resp.get("errors") or resp.get("error")
                    raise SilentPushExceptions(f"Connection failed: {error_msg}")
                return "ok"

            raise SilentPushExceptions(
                "Connection failed: Unexpected response format from API."
            )

        except SilentPushExceptions as e:
            res = e.details.get("res")
            if res is not None:
                if res.status_code == 401:
                    raise SilentPushExceptions(
                        "Authorization Error: make sure API Key is correctly set",
                        res=res,
                    )
                if res.status_code == 403:
                    raise SilentPushExceptions(
                        "Permission Error: Forbidden access. Check your API Key permissions.",
                        res=res,
                    )

            error_str = str(e)
            if "Forbidden" in error_str or "Authorization" in error_str:
                raise SilentPushExceptions(
                    "Authorization Error: make sure API Key is correctly set"
                )

            raise e
        except Exception as e:
            raise SilentPushExceptions(f"An unexpected error occurred: {str(e)}")

    def validate_ip_address(self, ip: str, allow_ipv6: bool = True) -> bool:
        """Validate an IP address.

        Args:
            ip: The IP address string to validate.
            allow_ipv6: Whether to allow IPv6 addresses.

        Returns:
            True if the IP address is valid according to the criteria, False otherwise.

        Raises:
            None: (Or omit if no errors are raised to the caller,
                but your prompt says 'Mandatory', so we list it).
        """
        try:
            ip = ip.strip()
            ip_obj = ipaddress.ip_address(ip)
            return not (not allow_ipv6 and ip_obj.version == 6)
        except ValueError:
            return False

    def get_enrichment_data(
        self,
        resource: str,
        value: str,
        explain: bool | None = False,
        scan_data: bool | None = False,
    ) -> dict:
        """
        Retrieve enrichment data for a specific resource.

        Args:
            resource (str): Type of resource (e.g., 'ip', 'domain').
            value (str): The specific value to enrich.
            explain (bool, optional): Whether to include detailed explanations. Defaults to False.
            scan_data (bool, optional): Whether to include scan data. Defaults to False.

        Returns:
            dict: Enrichment data for the specified resource.
        """
        endpoint = f"{ENRICHMENT}/{resource}/{value}"

        query_params = {
            "explain": 1 if explain else 0,
            "scan_data": 1 if scan_data else 0,
        }
        response = self._http_request(
            method="GET", url_suffix=endpoint, params=query_params
        )
        # Handle the response based on resource type
        if resource in ["ip", "ipv4", "ipv6"]:
            ip2asn_data = response.get("response", {}).get("ip2asn", [])
            return (
                ip2asn_data[0] if isinstance(ip2asn_data, list) and ip2asn_data else {}
            )
        return response.get("response", {})

    def validate_ips(self, ips: list[str]) -> None:
        """Validates the number of IPs in the list."""
        if len(ips) > 100:
            raise ValueError("Maximum of 100 IPs can be submitted in a single request.")

    def list_ip_information(self, ips: list[str], resource: str) -> dict:
        """
        Retrieve information for multiple IP addresses.

        Args:
            ips (List[str]): List of IPv4 or IPv6 addresses to fetch information for.
            resource (str): The resource type ('ipv4' or 'ipv6').

        Returns:
            Dict: API response containing IP information.
        """
        self.validate_ips(ips)

        ip_data = {"ips": ips}
        url_suffix = f"{LIST_IP}/{resource}"

        return self._http_request("POST", url_suffix, data=ip_data)

    def get_asn_reputation(
        self, asn: int, limit: int | None = None, explain: bool = False
    ) -> dict[str, Any]:
        """
        Retrieve reputation history for a specific Autonomous System
        Number (ASN).

        Args:
            asn (int): The Autonomous System Number to query.
            limit (int, optional): Maximum number of results to
                return. Defaults to None.
            explain (bool, optional): Whether to include explanation
            for reputation score. Defaults to False.

        Returns:
            Dict[str, Any]: ASN reputation history information.
        """
        params = {"explain": int(bool(explain)), "limit": limit}

        return self._http_request(
            method="GET", url_suffix=f"{ASN_REPUTATION}/{asn}", params=params
        )

    def get_asn_takedown_reputation(
        self, asn: str, explain: int = 0, limit: int = None
    ) -> dict[str, Any]:
        """
        Retrieve takedown reputation for a specific Autonomous System
        Number (ASN).

        Args:
            asn (str): The ASN number to query.
            limit (Optional[int]): Maximum results
                to return (default is None).
            explain (bool): Whether to include an explanation
                for the reputation score (default is False).

        Returns:
            Dict[str, Any]: Takedown reputation information
                for the specified ASN.
                Returns an empty dictionary if no takedown
                reputation is found.

        Raises:
            ValueError: If ASN is not provided.
            DemistoException: If the API call fails.
        """
        if not asn:
            raise ValueError("ASN is required.")

        url_suffix = f"{ASN_TAKEDOWN_REPUTATION}/{asn}"
        params = {"explain": int(bool(explain)), "limit": limit}

        raw_response = self._http_request(
            method="GET", url_suffix=url_suffix, params=params
        )
        return raw_response.get("response", {})

    def get_ipv4_reputation(
        self, ipv4: str, explain: bool = False, limit: int = None
    ) -> dict:
        """
        Retrieve historical reputation data for the specified IPv4 address.

        Args:
            ipv4 (str): The IPv4 address to check.
            explain (bool): Whether to include explanation details.
            limit (int): Maximum number of history entries to return.

        Returns:
            dict: Dictionary containing 'ip_reputation_history' key with list of entries.
        """
        url_suffix = f"{IPV4_REPUTATION}/{ipv4}"

        params = {"explain": int(bool(explain)), "limit": limit}

        params = {key: value for key, value in params.items() if value is not None}

        response = self._http_request(
            method="GET",
            url_suffix=url_suffix,
            params=params,
            headers={"Accept": CONTENT_TYPE, "Content-Type": CONTENT_TYPE},
        )

        if response.get("error") is not None:
            raise ValueError(f"API Error: {response['error']}")

        if isinstance(response, str):
            try:
                response = json.loads(response)
            except Exception as e:
                raise ValueError(f"Unable to parse JSON from response: {e}")

        data = response.get("response", {}).get("ip_reputation_history", [])

        return {"ip_reputation_history": data if isinstance(data, list) else []}

    def forward_padns_lookup(self, qtype: str, qname: str, **kwargs) -> dict[str, Any]:
        """
        Perform a forward PADNS lookup using various filtering parameters.

        Args:
            qtype (str): Type of DNS record.
            qname (str): The DNS record name to lookup.
            **kwargs: Optional parameters for filtering and pagination.

        Returns:
            Dict[str, Any]: PADNS lookup results.
        """
        url_suffix = f"{FORWARD_PADNS}/{qtype}/{qname}"

        params = kwargs
        params = {key: value for key, value in params.items() if value is not None}

        return self._http_request(method="GET", url_suffix=url_suffix, params=params)

    def reverse_padns_lookup(self, qtype: str, qname: str, **kwargs) -> dict[str, Any]:
        """
        Perform a reverse PADNS lookup using various filtering parameters.

        Args:
            qtype (str): Type of DNS record.
            qname (str): The DNS record name to lookup.
            **kwargs: Optional parameters for filtering and pagination.

        Returns:
            Dict[str, Any]: Reverse PADNS lookup results.
        """
        url_suffix = f"{REVERSE_PADNS}/{qtype}/{qname}"

        params = kwargs
        params = {key: value for key, value in params.items() if value is not None}

        return self._http_request(method="GET", url_suffix=url_suffix, params=params)

    def search_scan_data(self, query: str, **params: dict) -> dict[str, Any]:
        """
        Search the Silent Push scan data repositories.

        Args:
            query (str): Query in SPQL syntax to scan data (mandatory)
            params (dict): Optional parameters to filter scan data
        Returns:
            Dict[str, Any]: Search results from scan data repositories

        Raises:
            ValueError: If query is not provided or API call fails
        """
        if not query:
            raise ValueError("Query parameter is required for search scan data.")

        params = {
            "limit": params.get("limit"),
            "fields": params.get("fields"),
            "sort": params.get("sort"),
            "skip": params.get("skip"),
            "with_metadata": params.get("with_metadata"),
        }
        filter_params: dict = {
            key: value for key, value in params.items() if value is not None
        }
        url_suffix = SEARCH_SCAN

        payload = {"query": query}

        return self._http_request(
            method="POST", url_suffix=url_suffix, data=payload, params=filter_params
        )

    def live_url_scan(
        self,
        url: str,
        platform: str | None = None,
        os: str | None = None,
        browser: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """
        Perform a live scan of a URL to get hosting metadata.

        Args:
            url (str): The URL to scan.
            platform (str, optional): Device to perform scan with (Desktop, Mobile, Crawler).
            os (str, optional): OS to perform scan with (Windows, Linux, MacOS, iOS, Android).
            browser (str, optional): Browser to perform scan with (Firefox, Chrome, Edge, Safari).
            region (str, optional): Region from where scan should be performed (US, EU, AS, TOR).

        Returns:
            Dict[str, Any]: The scan results including hosting metadata.
        """
        url_suffix = LIVE_SCAN_URL

        params = {
            "url": url,
            "platform": platform,
            "os": os,
            "browser": browser,
            "region": region,
        }
        filter_params: dict = {
            key: value for key, value in params.items() if value is not None
        }

        print(filter_params)
        return self._http_request(
            method="GET", url_suffix=url_suffix, params=filter_params
        )

    def get_future_attack_indicators(
        self, feed_uuid: str, page_no: int = 1, page_size: int = 10000
    ) -> dict[str, Any]:
        """
        Retrieve indicators of future attack feed from SilentPush.

        Args:
            feed_uuid (str): Feed unique identifier to fetch records for.
            page_no (int, optional): Page number for pagination. Defaults to 1.
            page_size (int, optional): Number of records per page. Defaults to 10000.

        Returns:
            Dict[str, Any]: Response containing future attack indicators.
        """

        params = {"source_uuids": feed_uuid, "page": page_no, "limit": page_size}

        query_string = urlencode(params)
        url = (
            self.base_url.replace(MERGE_API, "")
            + f"/api/v2/iocs/threat-ranking/?{query_string}"
        )

        return self._http_request(method="GET", url=url)

    def screenshot_url(self, url: str) -> dict[str, Any]:
        """
        Generate a screenshot for a given URL and store it in the vault using GET request.

        Args:
            url (str): The URL to capture a screenshot of

        Returns:
            Dict[str, Any]: Response containing screenshot information and vault details
        """
        endpoint = SCREENSHOT_URL
        params = {"url": url if url is not None else None}

        response = self._http_request(method="GET", url_suffix=endpoint, params=params)
        if response.get("error"):
            return {"error": f"Failed to get screenshot: {response['error']}"}

        screenshot_data = response.get("response", {}).get("scan", {})
        if not screenshot_data:
            return {"error": "No screenshot data returned from API"}

        screenshot_url = screenshot_data.get("screenshot")
        if not screenshot_url:
            return {"error": "No screenshot URL returned"}

        return {
            "status_code": screenshot_data.get("response", 200),
            "screenshot_url": screenshot_url,
        }

    def add_feed(self, **args: dict) -> dict[str, Any]:
        """
        Add new feed on SilentPush.

        Args:
            args: Payload for filtering and pagination.

        Returns:
            Dict[str, Any]: Response containing feed information.
        """
        url = self.base_url.replace(MERGE_API, "") + f"{ADD_FEED}"
        tags_value = args.get("tags")
        tags_list = tags_value.split(",") if tags_value else None
        payload = {
            "name": args.get("name"),
            "type": args.get("type"),
            "vendor": args.get("vendor"),
            "feed_description": args.get("feed_description"),
            "category": args.get("category"),
            "tags": tags_list,
        }
        params = {key: value for key, value in payload.items() if value is not None}

        response = self._http_request(method="POST", url=url, data=params)

        if isinstance(response, dict) and response.get("errors"):
            return {"error": f"Failed to add new feed: {response['errors']}"}

        return response

    def add_feed_tags(self, **args: dict) -> dict[str, Any]:
        """
        Add new feed on SilentPush.

        Args:
            args: Payload for filtering and pagination.

        Returns:
            Dict[str, Any]: Response containing feed tags information.
        """
        feed_uuid = args.get("feed_uuid")
        url = (
            self.base_url.replace(MERGE_API, "")
            + f"{ADD_FEED}"
            + f"{feed_uuid}"
            + "/tags/"
        )
        tags_value = args.get("tags")
        tags_list = tags_value.split(",") if tags_value else None
        payload = {"tags": tags_list}
        params = {key: value for key, value in payload.items() if value is not None}
        response = self._http_request(method="POST", url=url, data=params)

        if isinstance(response, dict) and response.get("errors"):
            return {"error": f"Failed to add feed tags: {response['errors']}"}

        return response

    def add_indicators(self, **args: dict) -> dict[str, Any]:
        """
        Add new indicator on SilentPush.

        Args:
            args: Payload for filtering and pagination.

        Returns:
            Dict[str, Any]: Response containing indicators information.
        """
        feed_uuid = args.get("feed_uuid")
        url = (
            self.base_url.replace(MERGE_API, "")
            + f"{ADD_FEED}"
            + f"{feed_uuid}"
            + "/indicators/"
        )
        indicators_value = args.get("indicators")
        indicators_list = indicators_value.split(",") if indicators_value else None
        payload = {"indicators": indicators_list}
        params = {key: value for key, value in payload.items() if value is not None}
        response = self._http_request(method="POST", url=url, data=params)

        if isinstance(response, dict) and response.get("errors"):
            return {"error": f"Failed to add new indicators: {response['errors']}"}

        return response

    def add_indicators_tags(self, **args: dict) -> dict[str, Any]:
        """
        Add new indicator tags on SilentPush.

        Args:
            args: Payload for tags.

        Returns:
            Dict[str, Any]: Response containing indicator tags information.
        """
        feed_uuid = args.get("feed_uuid")
        indicator_name = args.get("indicator_name")
        url = (
            self.base_url.replace(MERGE_API, "")
            + f"{ADD_FEED}"
            + f"{feed_uuid}"
            + "/indicators/"
            + f"{indicator_name}"
            + "/update-tags/"
        )
        tags = args.get("tags")
        payload = {"tags": tags}
        params = {key: value for key, value in payload.items() if value is not None}
        response = self._http_request(method="PUT", url=url, data=params)

        if isinstance(response, dict) and response.get("errors"):
            return {"error": f"Failed to add indicator tags: {response['errors']}"}

        return response

    def run_threat_check(self, **args: dict) -> dict[str, Any]:
        """
        Fetch threat checks on SilentPush.

        Args:
            args: Params for threat checks.

        Returns:
            Dict[str, Any]: Response containing threat check information.
        """
        url = f"{THREAT_CHECK}"
        params = {
            "t": args.get("type"),
            "d": args.get("data"),
            "u": args.get("user_identifier"),
            "q": args.get("query"),
        }
        params = {key: value for key, value in params.items() if value is not None}
        response = self._http_request(method="GET", url=url, params=params)

        if isinstance(response, dict) and response.get("errors"):
            return {"error": f"Failed to run threat check: {response['errors']}"}

        return response

    def get_data_exports(self, feed_url: dict) -> requests.Response:
        """
        Exports data on SilentPush.

        Args:
            feed_url: Feed url for exporting data.

        Returns:
            Dict[str, Any]: Response containing feed information.
        """
        server_url = self.base_url.replace(MERGE_API, "")
        url = f"{server_url}{EXPORT_DATA}{feed_url}"

        response = requests.request(
            method="GET",
            url=url,  # <<< this must be full_url, not something else
            headers=self._headers,
        )

        return response
