from __future__ import annotations
from urllib.parse import urljoin
import requests
from .constants import ENDPOINTS
from .UtilsManager import validate_response
from .SymantecEmailSecurityCloudParser import SymantecEmailSecurityCloudParser


class SymantecEmailSecurityCloudManager:
    def __init__(
        self,
        api_root,
        username,
        password,
        verify_ssl,
        siemplify_logger=None,
        force_check_connectivity=False,
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} IOC API root of the Symantec Email Security.Cloud instance
        :param username: {str} Username of the Symantec Email Security.Cloud instance
        :param password: {str} Password of the Symantec Email Security.Cloud instance
        :param verify_ssl: {bool} Specifies if certificate that is configured on the api root should be validated
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.siemplify_logger = siemplify_logger
        self.parser = SymantecEmailSecurityCloudParser()
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.auth = (username, password)

        if force_check_connectivity:
            self.test_connectivity()

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
        url = self._get_full_url("ping")
        response = self.session.get(url)
        validate_response(response)

    def block_iocs(self, iocs_dict, remediation_action, description):
        """
        Block provided IOCs
        :param iocs_dict: {dict} Dictionary containing necessary information for blocking
        :param remediation_action: {str} Remediation action to make
        :param description: {str} Description to add
        :return: {list} List of IOCResult objects
        """
        url = self._get_full_url("block_entities")
        payload = []
        for identifier, data in iocs_dict.items():
            for ioc_type in data:
                payload.append(
                    {
                        "IocType": ioc_type,
                        "IocValue": identifier,
                        "Description": description,
                        "EmailDirection": "B",
                        "RemediationAction": remediation_action,
                    }
                )

        response = self.session.post(url, json=payload)
        validate_response(response)

        return self.parser.build_ioc_results_list(raw_data=response.json())
