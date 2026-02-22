# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests
import copy
import urllib.parse

# =====================================
#             CONSTANTS               #
# =====================================
# URLs
LOGIN_URL = "/auth/authentication-endpoint/authenticate/login?TENANTID={0}"  # Tenant ID
INCIDENTS_ACTIONS_URL = "/rest/{0}/ces"  # Tenant ID

# =====================================
#             PAYLOADS                #
# =====================================
LOGIN_PAYLOAD = {"Login": None, "Password": None}

CREATE_INCIDENT_PAYLOAD = {
    "entities": [
        {
            "entity_type": "Incident",
            "properties": {
                "DisplayLabel": "This incident opened from external system.",
                "Description": "Description of incident",
                "ImpactScope": "MultipleUsers",
                "Urgency": "SevereDisruption",
                "RegisteredForActualService": "20132",
            },
            "ext_properties": {
                "ExternalSystem": "SM",
                "Operation": "Create",
                "ExternalId": "20123",
                "ExternalEntityType": "Incident",
                "ExternalStatus": "Pending Vendor",
            },
        }
    ]
}

UPDATE_TICKET_PAYLOAD = {
    "entities": [
        {
            "entity_type": "Incident",
            "properties": {"Id": "10034"},
            "ext_properties": {
                "ExternalSystem": "SM",
                "Operation": "Update",
                "ExternalId": "IM20123",
                "ExternalEntityType": "Incident",
                "ExternalStatus": "Pending Vendor",
            },
        }
    ]
}

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Apache-HttpClient/4.4.1",
    "Cookie": "LWSSO_COOKIE_KEY={0}",
}


# =====================================
#              CLASSES                #
# =====================================
class MicroFocusITSMAManagerError(Exception):
    pass


class MicroFocusITSMAManager:
    def __init__(
        self,
        api_root,
        username,
        password,
        tenant_id,
        external_system,
        external_id="20123",
        verify_ssl=False,
    ):
        """
        :param api_root: api root url {string}
        :param username: access username {string}
        :param password: username's password {string}
        :param tenant_id: current tenant id {string}
        :param external_system: external system name {string}
        :param external_id: external id (20123 is the default value) {string}
        :param verify_ssl: verify certificate  {bool}
        """
        self.api_root = self.validate_api_root(api_root)
        self.username = username
        self.password = password
        self.tenant_id = tenant_id
        self.external_system = external_system
        self.external_id = external_id

        # Setup session.
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers = copy.deepcopy(HEADERS)
        self.session.headers["Cookie"] = self.session.headers["Cookie"].format(
            self.get_token()
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
            raise MicroFocusITSMAManagerError(
                f"Status Code: {http_response.status_code}, Content: {http_response.content}, Error: {err}"
            )

    def get_token(self):
        """
        Get connection token.
        :return: connection token {string}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, LOGIN_URL.format(self.tenant_id)
        )

        payload = copy.deepcopy(LOGIN_PAYLOAD)
        payload["Login"] = self.username
        payload["Password"] = self.password

        response = self.session.post(request_url, json=payload)

        self.validate_response(response)

        return response.content

    def create_incident(
        self,
        display_label="",
        description="",
        impact_scope="",
        urgency="",
        service_id="",
    ):
        """
        Create a new incident.
        :param display_label: incident's summery {string}
        :param description: incident's description {string}
        :param impact_scope: impact scope {string}
        :param urgency: incident's urgency {string}
        :param service_id: service id {string}
        :return: created ticket id {string}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, INCIDENTS_ACTIONS_URL.format(self.tenant_id)
        )

        # Setup payload.
        paylaod = copy.deepcopy(CREATE_INCIDENT_PAYLOAD)
        # Set properties.
        paylaod["entities"][0]["properties"]["DisplayLabel"] = display_label
        paylaod["entities"][0]["properties"]["Description"] = description
        paylaod["entities"][0]["properties"]["ImpactScope"] = impact_scope
        paylaod["entities"][0]["properties"]["Urgency"] = urgency
        paylaod["entities"][0]["properties"]["RegisteredForActualService"] = service_id
        # Set External properties.
        paylaod["entities"][0]["ext_properties"][
            "ExternalSystem"
        ] = self.external_system
        paylaod["entities"][0]["ext_properties"]["ExternalId"] = self.external_id

        response = self.session.post(request_url, json=paylaod)

        self.validate_response(response)

        return response.json()["entities"][0]["entity"]["properties"]["Id"]

    def update_incident(
        self,
        incident_id,
        display_label=None,
        description=None,
        impact_scope=None,
        urgency=None,
        service_id=None,
    ):
        """
        Update an incident.
        :param incident_id: id of the incident to update {string}
        :param display_label: incident's summery {string}
        :param description: incident's description {string}
        :param impact_scope: impact scope {string}
        :param urgency: incident's urgency {string}
        :param service_id: service id {string}
        :return: is succeed {bool}
        """

        request_url = urllib.parse.urljoin(
            self.api_root, INCIDENTS_ACTIONS_URL.format(self.tenant_id)
        )

        # Setup payload.
        paylaod = copy.deepcopy(UPDATE_TICKET_PAYLOAD)
        # Set ID
        paylaod["entities"][0]["properties"]["Id"] = incident_id
        # Set properties if inserted.
        if display_label:
            paylaod["entities"][0]["properties"]["DisplayLabel"] = display_label
        if description:
            paylaod["entities"][0]["properties"]["Description"] = description
        if impact_scope:
            paylaod["entities"][0]["properties"]["ImpactScope"] = impact_scope
        if urgency:
            paylaod["entities"][0]["properties"]["Urgency"] = urgency
        if service_id:
            paylaod["entities"][0]["properties"][
                "RegisteredForActualService"
            ] = service_id
        # Set External properties.
        paylaod["entities"][0]["ext_properties"][
            "ExternalSystem"
        ] = self.external_system
        paylaod["entities"][0]["ext_properties"]["ExternalId"] = self.external_id

        response = self.session.post(request_url, json=paylaod)

        self.validate_response(response)

        return True

    def update_external_incident_status(self, incident_id, status):
        """
        Update external incident status.
        :param incident_id: id of the incident to update {string}
        :param status: status to update {string}
        :return: is succeed {bool}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, INCIDENTS_ACTIONS_URL.format(self.tenant_id)
        )

        # Setup payload.
        paylaod = copy.deepcopy(UPDATE_TICKET_PAYLOAD)
        # Set ID
        paylaod["entities"][0]["properties"]["Id"] = incident_id

        # Set External properties.
        paylaod["entities"][0]["ext_properties"]["ExternalStatus"] = status
        paylaod["entities"][0]["ext_properties"][
            "ExternalSystem"
        ] = self.external_system
        paylaod["entities"][0]["ext_properties"]["ExternalId"] = self.external_id

        response = self.session.post(request_url, json=paylaod)

        self.validate_response(response)

        return True


#
