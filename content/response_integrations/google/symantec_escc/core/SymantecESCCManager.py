from __future__ import annotations
import requests
from urllib.parse import urljoin
from soar_sdk.SiemplifyUtils import utc_now, get_domain_from_entity
from soar_sdk.SiemplifyDataModel import EntityTypes
from symantec_escc.core.SymantecESCCParser import SymantecESCCParser
from symantec_escc.core.UtilsManager import validate_response

from symantec_escc.core.constants import ENDPOINTS, BLOCKED_STATE, UNKNOWN_STATE, NETWORK_KEY, FILE_KEY


class SymantecESCCManager:
    def __init__(
        self,
        api_root=None,
        client_id=None,
        client_secret=None,
        verify_ssl=False,
        siemplify_logger=None,
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: Symantec Endpoint Security Complete Cloud API root.
        :param client_id: Symantec Endpoint Security Complete Cloud Client ID.
        :param client_secret: Symantec Endpoint Security Complete Cloud Client Secret.
        :param verify_ssl: If enabled, verify the SSL certificate for the connection to the Symantec Endpoint Security Complete Cloud server is valid.
        :param siemplify_logger: Siemplify logger.
        """

        self.api_root = api_root if api_root[-1:] == "/" else api_root + "/"
        self.client_id = client_id
        self.client_secret = client_secret
        self.siemplify_logger = siemplify_logger

        self.parser = SymantecESCCParser()
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.access_token = self.generate_token(self.client_id, self.client_secret)
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }
        )

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def generate_token(self, client_id, client_secret):
        """
        :param client_id: {string} Symantec Endpoint Security Complete Cloud Client ID
        :param client_secret: {string} Symantec Endpoint Security Complete Cloud Client Secret.
        :return: {string} Access token. The app can use this token in API requests
        """
        request_url = self._get_full_url("access_token")
        payload = {"client_id": client_id, "client_secret": client_secret}
        res = requests.post(request_url, data=payload)
        validate_response(res)
        return res.json().get("access_token")

    def test_connectivity(self):
        """
        Test integration to the Symantec Endpoint Security Complete.
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("test_connectivity")
        formatted_time = (
            utc_now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
            + utc_now().strftime("%z")[:3]
            + ":"
            + utc_now().strftime("%z")[3:]
        )
        payload = {"start_date": formatted_time, "end_date": formatted_time, "limit": 1}
        result = self.session.post(request_url, json=payload)
        validate_response(result)

    def get_device_groups(self):
        """
        Get available device groups
        :return: {list} List of Device group objects
        """
        request_url = self._get_full_url("get_device_groups")
        response = self.session.get(request_url)
        validate_response(response)
        return self.parser.build_list_of_device_groups(response.json())

    def get_devices_in_group(self, group_id):
        """
        Get all devices in device group
        :param group_id: {str} Id of the group
        :return: {list} List of Device objects
        """
        request_url = self._get_full_url("get_devices_in_group", group_id=group_id)
        response = self.session.get(request_url)
        validate_response(response)
        return self.parser.build_list_of_devices(response.json())

    def get_device_by_id(self, device_id):
        """
        Get device details by its id
        :param device_id: {str} Id of the device
        :return: {Device} Device object
        """
        request_url = self._get_full_url("get_device_by_id", device_id=device_id)
        response = self.session.get(request_url)
        validate_response(response)
        return self.parser.build_device_obj(response.json())

    def get_entity_information(self, ioc_type, identifier):
        """
        Get entity details with identifier
        :param ioc_type: {str} IOC type of entity (network/file)
        :param identifier: {str} Entity identifier
        :return: {EntityDetails} EntityDetails object
        """
        request_url = self._get_full_url(
            "get_entity_details", ioc_type=ioc_type, identifier=identifier
        )
        response = self.session.get(request_url)
        validate_response(response)
        return self.parser.build_entity_details_obj(response.json())

    def get_hash_related_processes_info(self, filehash):
        """
        Get information about the processes related to Hash
        :param filehash: {str} The filehash to use in request
        :return: {dict}
        """
        request_url = self._get_full_url("get_hash_processes", filehash=filehash)
        response = self.session.get(request_url)
        validate_response(response)
        return response.json().get("chain", {})

    def get_antivirus_information(self, ioc_type, identifier):
        """
        Get antivirus information about the Entity
        :param ioc_type: {str} IOC type of entity (network/file)
        :param identifier: {str} Entity identifier
        :return: {bool} True, if response contains state of the entity
        """
        request_url = self._get_full_url(
            "get_antivirus_info", ioc_type=ioc_type, identifier=identifier
        )
        response = self.session.get(request_url)
        validate_response(response)
        if response.json().get("state"):
            return True

    def get_full_entity_details(self, entity):
        """
        Get all required information for entity
        :param entity: {entity}
        :return: {EntityDetails} EntityDetails object
        """
        ioc_type = (
            FILE_KEY if entity.entity_type == EntityTypes.FILEHASH else NETWORK_KEY
        )
        identifier = (
            get_domain_from_entity(entity)
            if entity.entity_type == EntityTypes.URL
            else entity.identifier
        )
        entity_details = self.get_entity_information(
            ioc_type=ioc_type, identifier=identifier
        )
        if len(entity_details.to_json()) < 2 and any(
            key in entity_details.to_json() for key in (NETWORK_KEY, FILE_KEY)
        ):
            return None

        if entity.entity_type == EntityTypes.FILEHASH:
            entity_details.raw_data["process_chain"] = (
                self.get_hash_related_processes_info(entity.identifier)
            )

        entity_details.state = (
            BLOCKED_STATE
            if self.get_antivirus_information(ioc_type, identifier)
            else UNKNOWN_STATE
        )
        entity_details.raw_data["state"] = entity_details.state
        return entity_details

    def get_related_iocs(self, entity):
        """
        Get IOCs related to the entity
        :param entity: {Entity} Siemplify Entity object
        :return: {list} List of Related IOCs objects
        """
        ioc_type = (
            FILE_KEY if entity.entity_type == EntityTypes.FILEHASH else NETWORK_KEY
        )
        identifier = (
            get_domain_from_entity(entity)
            if entity.entity_type == EntityTypes.URL
            else entity.identifier
        )
        request_url = self._get_full_url(
            "get_related_iocs", ioc_type=ioc_type, identifier=identifier
        )
        response = self.session.get(request_url)
        validate_response(response)
        return self.parser.build_list_of_related_iocs(response.json())
