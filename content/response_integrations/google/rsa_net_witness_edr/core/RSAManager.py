from __future__ import annotations
import requests
from urllib.parse import urljoin
import json
import copy
from rsa_net_witness_edr.core.RSAParser import RSAParser
from soar_sdk.SiemplifyDataModel import EntityTypes
from rsa_net_witness_edr.core.RSAExceptions import RSAError, MachineDoesntExistError

from rsa_net_witness_edr.core.constants import (
    REQUEST_HEADERS,
    PING_QUERY,
    ADD_IP_TO_BLOCKLIST,
    ADD_URL_TO_BLOCKLIST,
    GET_ENDPOINT_HOSTNAME_GUID,
    GET_ENDPOINT_IP_GUID,
    GET_ENDPOINT_DETAILS,
    GET_ENDPOINT_IOCS,
    GET_IOC_DETAIL,
)


class RSAManager:
    def __init__(
        self,
        api_root=None,
        username=None,
        password=None,
        verify_ssl=False,
        siemplify_logger=None,
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: API Root of the RSA Netwitness EDR instance.
        :param username: RSA Netwitness EDR username.
        :param password: RSA Netwitness EDR password.
        :param verify_ssl: If enabled, verify the SSL certificate for the connection to the RSA Netwitness EDR server is valid.
        :param siemplify_logger: Siemplify logger.
        """

        self.api_root = api_root if api_root[-1:] == "/" else api_root + "/"
        self.username = username
        self.password = password
        self.siemplify_logger = siemplify_logger

        self.parser = RSAParser()
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.auth = (self.username, self.password)
        self.session.headers = copy.deepcopy(REQUEST_HEADERS)

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                response.json()
            except:
                # Not a JSON - return content
                raise RSAError(f"{error_msg}: {error} - {error.response.content}")

            raise RSAError(
                f"{error_msg}: {response.json().get('name')} {json.dumps(response.json())}"
            )

    def test_connectivity(self):
        """
        Test integration connectivity.
        :return: {bool}
        """

        request_url = f"{self.api_root}{PING_QUERY}"
        result = self.session.get(request_url)
        # Verify result.
        self.validate_response(result)

        return False

    def add_url_to_blocklist(self, urls_to_blocklist):
        """
        Function that adds a URL to blocklist
        :param urls_to_blocklist: {List} List of URLs that will be added to blocklist
        :return: Domains object
        """

        payload = {"Domains": urls_to_blocklist}

        url = urljoin(self.api_root, ADD_URL_TO_BLOCKLIST)

        response = self.session.post(url, json=payload)
        self.validate_response(response)

        return self.parser.build_domains_object(response.json())

    def add_ip_to_blocklist(self, ips_to_blocklist):
        """
        Function that adds a list of IPs to blocklist
        :param ips_to_blocklist: {List} List of URLs that will be added to blocklist
        :return: IPs object
        """

        payload = {"IPs": ips_to_blocklist}

        url = urljoin(self.api_root, ADD_IP_TO_BLOCKLIST)

        response = self.session.post(url, json=payload)
        self.validate_response(response)

        return self.parser.build_ips_object(response.json())

    def get_ip_guid(self, entity_id):
        """
        Function that gets the GUID of an IP address
        :param entity_id: {string} Id of the entity that should be processed
        :return: Entity GUID
        """
        url = urljoin(self.api_root, GET_ENDPOINT_IP_GUID.format(entity_id))

        response = self.session.get(url)
        self.validate_response(response)

        if response.json().get("Items", []):
            return response.json().get("Items", [])[0].get("Id")

        raise MachineDoesntExistError("Machine doesn't exist in EDR")

    def get_hostname_guid(self, entity_id):
        """
        Function that gets the GUID of a host name
        :param entity_id: {string} Id of the entity that should be processed
        :return: Entity GUID
        """

        url = urljoin(self.api_root, GET_ENDPOINT_HOSTNAME_GUID.format(entity_id))

        response = self.session.get(url)
        self.validate_response(response)

        if response.json().get("Items", []):
            return response.json().get("Items", [])[0].get("Id")

        raise MachineDoesntExistError("Machine doesn't exist in EDR")

    def get_endpoint_details(self, endpoint_gui):
        """
        Function that fetches endpoint details from RSA EDR
        :param endpoint_gui: {string} GUID of an entity in RSA EDR
        :return: Machine object
        """
        url = urljoin(self.api_root, GET_ENDPOINT_DETAILS.format(endpoint_gui))

        response = self.session.get(url)
        self.validate_response(response)

        return self.parser.build_machine_object(response.json())

    def get_endpoint_iocs(self, entity_id, entity_type, max_iocs_to_return):
        """
        Function that fetches endpoint IOCS from RSA EDR
        :param entity_id: {string}  Id of the entity that should be processed
        :param entity_type: {string} EntityType of the processed entity
        :param max_iocs_to_return: {int} Limit od IOCS to return
        :return: {JSON} JSON object of IOCS objects
        """

        if entity_type == EntityTypes.ADDRESS:
            endpoint_gui = self.get_ip_guid(entity_id=entity_id)
        if entity_type == EntityTypes.HOSTNAME:
            endpoint_gui = self.get_hostname_guid(entity_id=entity_id)

        url = urljoin(
            self.api_root, GET_ENDPOINT_IOCS.format(endpoint_gui, max_iocs_to_return)
        )

        response = self.session.get(url)
        self.validate_response(response)

        iocs_details = response.json().get("Iocs", [])
        iocs_details_list = [
            self.parser.build_iocs_object(ioc_data) for ioc_data in iocs_details
        ]

        return self.parser.build_iocs_object_json(iocs_details_list)

    def enrich_endpoint(self, entity_id, entity_type):
        """
        Function that gets all the data needed for enrichment
        :param entity_id: {string} Id of the entity that should be processed
        :param entity_type: {string} Type of the entitiy that should be processed
        :return: Machine Object
        """

        if entity_type == EntityTypes.ADDRESS:
            endpoint_gui = self.get_ip_guid(entity_id=entity_id)
        if entity_type == EntityTypes.HOSTNAME:
            endpoint_gui = self.get_hostname_guid(entity_id=entity_id)

        endpoint_details = self.get_endpoint_details(endpoint_gui=endpoint_gui)

        return endpoint_details

    def enrich_entities(self, entity_id):
        """
        Function that gets all the data needed for enrichment of an entity
        :param entity_id: {string} Id of the entity that should be processed
        :return: IOCLevel Object
        """
        url = urljoin(self.api_root, GET_IOC_DETAIL.format(entity_id))

        response = self.session.get(url)
        self.validate_response(response)

        return self.parser.build_ioclevel_object(response.json())
