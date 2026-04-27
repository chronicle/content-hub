# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests
import base64
import copy
import urllib.parse
import json
import xmltodict
from .CiscoISEParser import CiscoISEParser

# =====================================
#             CONSTANTS               #
# =====================================
# ---- Headers. ----
BASIC_HEADER = {"Accept": "application/json"}

JSON_CONTENT_TYPE_STRING = "Application/Json"

FIRST_UI_LOGIN_REQUEST_HEADER = {"Referer": "https://x.x.x.x/admin/"}

SECOND_UI_LOGIN_REQUEST_HEADER = headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": "https://x.x.x.x/admin/login.jsp",
    "Cookie": "testcookieenabled; APPSESSIONID={0}",
}

GET_ENDPOINT_MAC_BY_IP_REQUEST_HEADER = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://x.x.x.x/admin/",
    "content-type": "application/json",
    "Connection": "keep-alive",
    "Cookie": "testcookieenabled; APPSESSIONID={}",  # {0} - Session id from previous request.(Second UI login request)
    "User-Agent": "mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36",
    "_QPH_": "base64(GET_ENDPOINTS_MAC_QUERY)",
}

# --- Payloads. ----
QUARANTINE_ENDPOINT_PAYLOAD = {
    "OperationAdditionalData": {
        "additionalData": [
            {"name": "policyName", "value": "Relevant Policy Name"},
            {"name": "macAddress", "value": "Relevant IP address"},
        ]
    }
}


UNQUARANTINE_ENDPOINT_PAYLOAD = {
    "OperationAdditionalData": {
        "additionalData": [{"name": "macAddress", "value": "Relevant IP address"}]
    }
}


SECOND_UI_LOGIN_REQUEST_DATA = "username={0}&password={1}&rememberme=on&name={0}&password={1}&authType=Internal&newPassword=&destinationURL=&xeniaUrl=&locale=en&hasSelectedLocale=false"  # {0} - Username, {1} - Password

# --- Queries. ----
GET_ENDPOINTS_MAC_QUERY = "exactMatch=true&pageType=app&ip={0}&columns=MACAddress,userName,EndPointPolicy,ip,Location,operating-system-result&sortBy=userName"  # {0} - Endpoint's IP address.


# ---- URLs. ----
QUARANTINE_ENDPOINT_URL = "/ers/config/ancendpoint/apply"
UNQUARANTINE_ENDPOINT_URL = "/ers/config/ancendpoint/clear"
GET_ENDPOINTS_URL = "/ers/config/endpoint"
GET_ENDPOINT_BY_NAME_URL = (
    "/ers/config/endpoint/name/{0}"  # {0} - Endpoint MAC Address.
)
GET_ENDPOINT_BY_ID_URL = "/ers/config/endpoint/{0}"  # {0} - Endpoint ID.
GET_SESSION_URL = "/ers/config/sessionservicenode"
TERMINATE_SESSION_URL = "/admin/API/mnt/CoA/Disconnect/{0}/{1}/{2}"  # {0} - Node Server Name , {1} - Calling_Station_ID, {2} - Terminate Type.
FIND_ENDPOINT_GROUP_URL = (
    "/admin/API/mnt/CoA/Reauth/{0}/{1}/1"  # {0} - Node Server Name , {1} - MAC Address
)
GET_ENDPOINT_GROUPS = "/ers/config/endpointgroup"
ADD_ENDPOINT_TO_GROUP_URL = "/ers/config/endpoint/{0}"  # {0} - Endpoint ID.

# -  UI API URLs. -
# login
FIRST_UI_LOGIN_REQUEST_REFERER_URL = "/admin/"
FIRST_UI_LOGIN_REQUEST_URL = "/admin/login.jsp"
SECOND_UI_LOGIN_REQUEST_URL = "/admin/LoginAction.do"
GET_ENDPOINT_ENRICHMENT_URL = (
    "/admin/rs/uiapi/visibility/endpoint/{0}"  # {0} - Endpoint MAC address.
)
# Query
GET_ENDPOINT_MAC_BY_IP_URL = "/admin/rs/uiapi/visibility/"

FILTER_KEY_MAPPING = {
    "Select One": "",
    "Name": "name",
    "ID": "id",
    "Description": "description",
}

FILTER_STRATEGY_MAPPING = {"Not Specified": "", "Equal": "EQ", "Contains": "CONTAINS"}


# =====================================
#              CLASSES                #
# =====================================
class CiscoISEManagerError(Exception):
    pass


class CiscoISEManager:
    def __init__(
        self, api_root, username, password, verify_requests=False, logger=None
    ):
        self.api_root = self.validate_api_root(api_root)
        self.username = username
        self.password = password
        self.logger = logger
        self.parser = CiscoISEParser()
        # API Session.
        self.session = requests.session()
        self.session.verify = verify_requests
        # UI API Session.
        self.ui_session = None

        # Prepare and Attach headers.
        self.session.headers = copy.deepcopy(BASIC_HEADER)

        # Authenticate.
        self.session.auth = (username, password)
        self.login_ui_api()
        self.ping()

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

    @staticmethod
    def validate_response(http_response):
        """
        Validated an HTTP response.
        :param http_response: HTTP response object.
        :return: {void}
        """
        try:
            http_response.raise_for_status()

        except requests.HTTPError as err:
            raise CiscoISEManagerError(err)

    @staticmethod
    def remove_port_from_url(url):
        """
        Remove the port from the url.
        :param url: URL {string}
        :return: URL {string}
        """
        if ":" in url:
            return f"{url.split(':')[0]}:{url.split(':')[1]}/"
        else:
            return url

    def login_ui_api(self):
        """
        Provides login to the Cisco ISE UI API.
        :return: {HTTP Session}
        """
        # Get rid of the port at the API Root.
        api_root = self.remove_port_from_url(self.api_root)

        self.ui_session = requests.session()
        self.ui_session.verify = self.session.verify

        # - First login request. -
        first_request_uri = urllib.parse.urljoin(api_root, FIRST_UI_LOGIN_REQUEST_URL)

        # Organize headers for first request.
        headers = copy.deepcopy(FIRST_UI_LOGIN_REQUEST_HEADER)
        headers["Referer"] = urllib.parse.urljoin(
            api_root, FIRST_UI_LOGIN_REQUEST_REFERER_URL
        )

        first_request_response = self.ui_session.get(first_request_uri, headers=headers)
        # Fetch app session id
        first_session_id = self.ui_session.cookies["APPSESSIONID"]

        # - Second login request. -

        second_request_uri = urllib.parse.urljoin(api_root, SECOND_UI_LOGIN_REQUEST_URL)

        # Organize headers for second request.
        headers = copy.deepcopy(SECOND_UI_LOGIN_REQUEST_HEADER)
        headers["Referer"] = first_request_uri
        headers["Cookie"] = headers["Cookie"].format(first_session_id)

        # Organize payload.
        payload = SECOND_UI_LOGIN_REQUEST_DATA.format(self.username, self.password)

        # Produce the second login call with the cookie from the first one.
        second_request_response = self.ui_session.post(
            second_request_uri, data=payload, headers=headers
        )

    def ping(self):
        """
        Test CiscoISE integration test(By sending simple get request).
        :return: is succeed {bool}
        """
        request_url = urllib.parse.urljoin(self.api_root, GET_SESSION_URL)
        response = self.session.get(request_url)
        self.validate_response(response)
        response.json()
        return True

    def get_endpoint_mac_by_ip(self, ip_address):
        """
        Get endpoint's mac address by IP address.
        :param ip_address: endpoint's ip address {string}
        :return: endpoint's mac address {string}
        """
        ui_api_root = self.remove_port_from_url(self.api_root)

        # Initialize UI API session.
        self.login_ui_api()

        # Fetch session id.
        try:
            session_id = self.ui_session.cookies["APPSESSIONID"]
        except KeyError as err:
            raise CiscoISEManagerError(
                f'Bad UI API login, missing "APPSESSIONID", ERROR: {err}'
            )

        request_url = urllib.parse.urljoin(ui_api_root, GET_ENDPOINT_MAC_BY_IP_URL)

        # Build query request headers.

        # headers are individual for each request.
        headers = copy.deepcopy(GET_ENDPOINT_MAC_BY_IP_REQUEST_HEADER)
        headers["Referer"] = urllib.parse.urljoin(
            ui_api_root, FIRST_UI_LOGIN_REQUEST_REFERER_URL
        )
        headers["Cookie"] = headers["Cookie"].format(session_id)
        headers["_QPH_"] = base64.b64encode(
            GET_ENDPOINTS_MAC_QUERY.format(ip_address).encode("utf-8")
        )

        response = self.ui_session.get(request_url, headers=headers)

        self.validate_response(response)

        try:
            return json.loads(response.json()[0])["MACAddress"]
        except Exception as err:
            raise CiscoISEManagerError(
                f'No mac address for ip address "{ip_address}", ERROR: {err}'
            )

    def quarantine_endpoint(self, endpoint_address, quarantine_policy_name):
        """
        Quarantine an endpoint by attaching it to a policy.
        :param endpoint_address: Endpoint's IP address.
        :param quarantine_policy_name: Policy name to attach the endpoint to.
        :return: is success {bool}
        """
        request_url = urllib.parse.urljoin(self.api_root, QUARANTINE_ENDPOINT_URL)
        # Organize Payload.
        payload = copy.deepcopy(QUARANTINE_ENDPOINT_PAYLOAD)
        payload["OperationAdditionalData"]["additionalData"][0][
            "value"
        ] = quarantine_policy_name
        payload["OperationAdditionalData"]["additionalData"][1][
            "value"
        ] = endpoint_address

        response = self.session.put(request_url, json=payload)
        self.validate_response(response)
        return True

    def unquarantine_endpoint(self, endpoint_address):
        """
        Quarantine an endpoint by attaching it to a policy.
        :param endpoint_address: Endpoint's IP address.
        :param quarantine_policy_name: Policy name to attach the endpoint to.
        :return: is success {bool}
        """
        request_url = urllib.parse.urljoin(self.api_root, UNQUARANTINE_ENDPOINT_URL)
        # Organize Payload.
        payload = copy.deepcopy(UNQUARANTINE_ENDPOINT_PAYLOAD)
        payload["OperationAdditionalData"]["additionalData"][0][
            "value"
        ] = endpoint_address

        response = self.session.put(request_url, json=payload)
        self.validate_response(response)
        return True

    def get_endpoints(self):
        """
        Get list of endpoint objects.
        :return: list of dict when each dict is a endpoint object. {list}
        """
        result_list = []
        request_url = urllib.parse.urljoin(self.api_root, GET_ENDPOINTS_URL)
        response = self.session.get(request_url)
        self.validate_response(response)
        search_result = response.json().get("SearchResult")
        if search_result and search_result.get("resources"):
            endpoints_ids = [
                endpoint_resource["id"]
                for endpoint_resource in search_result.get("resources")
            ]
            for endpoints_id in endpoints_ids:
                try:
                    endpoint_obj = self.get_endpoint_by_id(endpoints_id)
                    if endpoint_obj.get("ERSEndPoint"):
                        result_list.append(endpoint_obj.get("ERSEndPoint"))
                except:
                    # If entity does not exist just pass to the next one.
                    pass

        return result_list

    def get_sessions(self):
        """
        Get sessions list.
        :return: list of dicts when each disc is a session object {list}
        """
        request_url = urllib.parse.urljoin(self.api_root, GET_SESSION_URL)
        response = self.session.get(request_url)
        self.validate_response(response)

        return response.json().get("SearchResult", {}).get("resources")

    def get_endpoint_by_mac(self, endpoint_address):
        """
        Get single endpoint by mac address.
        :param endpoint_address: endpoint address {string}
        :return: endpoint information {dict}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, GET_ENDPOINT_BY_NAME_URL.format(endpoint_address)
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()

    def get_endpoint_by_id(self, endpoint_id):
        """
        Get endpoint object by it's id.
        :param endpoint_id: endpoint id {string}
        :return: endpoint information {dict}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, GET_ENDPOINT_BY_ID_URL.format(endpoint_id)
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()

    def get_endpoint_enrichment(self, mac_address):
        """
        Get more enrichment data about an entity.
        :param mac_address: endpoint's mac address {string}
        :return: entity enrichment data {dict}
        """
        # Remove port from
        api_root = self.remove_port_from_url(self.api_root)

        # Initialize UI API session.
        self.login_ui_api()

        # fetch session id.
        try:
            session_id = self.ui_session.cookies["APPSESSIONID"]
        except KeyError as err:
            raise CiscoISEManagerError(
                f'Bad UI API login, missing "APPSESSIONID", ERROR: {err}'
            )

        # Organize header
        headers = copy.deepcopy(SECOND_UI_LOGIN_REQUEST_HEADER)
        headers["Cookie"] = headers["Cookie"].format(session_id)
        headers["Referer"] = urllib.parse.urljoin(
            api_root, FIRST_UI_LOGIN_REQUEST_REFERER_URL
        )
        headers["Content-Type"] = JSON_CONTENT_TYPE_STRING

        request_url = urllib.parse.urljoin(
            api_root, GET_ENDPOINT_ENRICHMENT_URL.format(mac_address)
        )
        response = self.ui_session.get(request_url, headers=headers)
        self.validate_response(response)
        return response.json()

    def update_endpoint(
        self,
        mac_address,
        description=None,
        group_id=None,
        portal_user=None,
        identity_store=None,
        identity_store_id=None,
        custom_attributes={},
        mdm_server_name=None,
        mdm_reachable=None,
        mdm_enrolled=None,
        mdm_compliance_status=None,
        mdm_os=None,
        mdm_manufacturer=None,
        mdm_model=None,
        mdm_encrypted=None,
        mdm_pinlock=None,
        mdm_jail_broken=None,
        mdm_imei=None,
        mdm_phone_number=None,
    ):
        """
        Update endpoint object.
        :param mac_address: Endpoint's MAC address {string}
        :param description: endpoint's property to update {string}
        :param group_id: endpoint's property to update {string}
        :param portal_user: endpoint's property to update {string}
        :param identity_store: endpoint's property to update {string}
        :param identity_store_id: endpoint's property to update {string}
        :param custom_attributes: if there are custom attributes to add they will be added to the entity object {dict}
        :param mdm_server_name: endpoint's property to update {string}
        :param mdm_reachable: endpoint's property to update {bool}
        :param mdm_enrolled: endpoint's property to update {bool}
        :param mdm_compliance_status: endpoint's property to update {bool}
        :param mdm_os: endpoint's property to update {string}
        :param mdm_manufacturer: endpoint's property to update {string}
        :param mdm_model: endpoint's property to update {string}
        :param mdm_encrypted: endpoint's property to update {bool}
        :param mdm_pinlock: endpoint's property to update {bool}
        :param mdm_jail_broken: endpoint's property to update {bool}
        :param mdm_imei: endpoint's property to update {string}
        :param mdm_phone_number: endpoint's property to update {string}
        :return: is success {bool}
        """
        # Fetch property object.
        entity_object = self.get_endpoint_by_mac(mac_address)

        # Fetch endpoint id.
        try:
            endpoint_id = entity_object["ERSEndPoint"]["id"]
        except Exception as err:
            raise CiscoISEManagerError(
                f"Error fetching endpoint object id, ERROR: {err}"
            )

        # Update endpoint object.
        try:
            if description:
                entity_object["ERSEndPoint"]["description"] = description
            if group_id:
                entity_object["ERSEndPoint"]["groupId"] = group_id
            if portal_user:
                entity_object["ERSEndPoint"]["portalUser"] = portal_user
            if identity_store:
                entity_object["ERSEndPoint"]["identityStore"] = identity_store
            if identity_store_id:
                entity_object["ERSEndPoint"]["identityStoreId"] = identity_store_id
            if custom_attributes:
                entity_object["ERSEndPoint"]["customAttributes"][
                    "customAttributes"
                ].update(custom_attributes)
            if mdm_server_name:
                entity_object["ERSEndPoint"]["mdmAttributes"][
                    "mdmServerName"
                ] = mdm_server_name
            if mdm_os:
                entity_object["ERSEndPoint"]["mdmAttributes"]["mdmOS"] = mdm_os
            if mdm_manufacturer:
                entity_object["ERSEndPoint"]["mdmAttributes"][
                    "mdmManufacturer"
                ] = mdm_manufacturer
            if mdm_model:
                entity_object["ERSEndPoint"]["mdmAttributes"]["mdmModel"] = mdm_model
            if mdm_imei:
                entity_object["ERSEndPoint"]["mdmAttributes"]["mdmIMEI"] = mdm_imei
            if mdm_phone_number:
                entity_object["ERSEndPoint"]["mdmAttributes"][
                    "mdmPhoneNumber"
                ] = mdm_phone_number

            # Bool Variables.
            if mdm_encrypted is not None:
                entity_object["ERSEndPoint"]["mdmAttributes"][
                    "mdmEncrypted"
                ] = mdm_encrypted
            if mdm_pinlock is not None:
                entity_object["ERSEndPoint"]["mdmAttributes"][
                    "mdmPinlock"
                ] = mdm_pinlock
            if mdm_jail_broken is not None:
                entity_object["ERSEndPoint"]["mdmAttributes"][
                    "mdmJailBroken"
                ] = mdm_jail_broken
            if mdm_reachable is not None:
                entity_object["ERSEndPoint"]["mdmAttributes"][
                    "mdmReachable"
                ] = mdm_reachable
            if mdm_enrolled is not None:
                entity_object["ERSEndPoint"]["mdmAttributes"][
                    "mdmEnrolled"
                ] = mdm_enrolled
            if mdm_compliance_status is not None:
                entity_object["ERSEndPoint"]["mdmAttributes"][
                    "mdmComplianceStatus"
                ] = mdm_compliance_status

        except Exception as err:
            raise CiscoISEManagerError(f"Endpoint does not have property, ERROR: {err}")

        request_url = urllib.parse.urljoin(
            self.api_root, GET_ENDPOINT_BY_ID_URL.format(endpoint_id)
        )
        response = self.session.put(request_url, json=entity_object)
        self.validate_response(response)
        return True

    def terminate_session(self, node_server_name, calling_station_id, terminate_type=0):
        """
        Terminate ISE API session.
        :param node_server_name: ise node server name {string}
        :param calling_station_id: calling station id {string}
        :param terminate_type: termination type - 0:DYNAMIC_AUTHZ_PORT_DEFAULT  1:DYNAMIC_AUTHZ_PORT_BOUNCE  2:DYNAMIC_AUTHZ_PORT_SHUTDOWN {integer}
        :return: is succeed {bool}
        """
        requset_url = urllib.parse.urljoin(
            self.remove_port_from_url(self.api_root),
            TERMINATE_SESSION_URL.format(
                node_server_name, calling_station_id, terminate_type
            ),
        )

        response = self.session.get(
            requset_url, auth=(self.username, self.password), headers={}
        )

        self.validate_response(response)

        return True

    def reauthenticate_endpoint(self, node_server_name, mac_address):
        """
        Reauthenticate endpoint.
        :param node_server_name: ise node server name {string}
        :param mac_address: endpoint {string}
        :return: {json}
        """
        request_url = urllib.parse.urljoin(
            self.remove_port_from_url(self.api_root),
            FIND_ENDPOINT_GROUP_URL.format(node_server_name, mac_address),
        )

        response = self.session.get(
            request_url, auth=(self.username, self.password), headers={}
        )

        self.validate_response(response)

        return json.loads(json.dumps(xmltodict.parse(response.content)))

    def get_endpoint_groups(self, filter_key, filter_logic, filter_value, limit):
        """
        List available endpoint entity groups
        :param filter_key: {str} Filter key to use for results filtering
        :param filter_logic: {str} Filter logic
        :param filter_value: {str} Filter value
        :param limit: {str} Limit for results
        :return: {list}
        """
        request_url = urllib.parse.urljoin(
            self.remove_port_from_url(self.api_root), GET_ENDPOINT_GROUPS
        )
        params = {"size": limit}
        if filter_value and filter_logic:
            params["filter"] = (
                f"{filter_key.lower()}.{filter_logic.upper()}.{filter_value}"
            )

        response = self.session.get(request_url, params=params)
        self.validate_response(response)

        return self.parser.build_endpoint_groups_list(response.json())

    def add_endpoint_to_group(self, endpoint_id, group_id):
        """
        Add endpoint to endpoint group.
        :param endpoint_id: {str} endpoint id
        :param group_id: {str} group id
        :return: {json}
        """
        request_url = urllib.parse.urljoin(
            self.remove_port_from_url(self.api_root),
            ADD_ENDPOINT_TO_GROUP_URL.format(endpoint_id),
        )
        payload = {"ERSEndPoint": {"groupId": group_id}}
        response = self.session.put(request_url, json=payload)
        self.validate_response(response)

        return response.json()
