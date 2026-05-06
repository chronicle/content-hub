# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
from urllib.parse import urljoin
import requests
from .UtilsManager import validate_response
from .HCLBigFixInventoryParser import HCLBigFixInventoryParser
from .constants import ENDPOINTS


class HCLBigFixInventoryManager:
    def __init__(self, api_root, api_token, verify_ssl, siemplify_logger=None):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} HCLBigFixInventory API root
        :param api_token: {str} HCLBigFixInventory API token
        :param verify_ssl: {bool} Specifies if certificate that is configured on the api root should be validated
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.api_token = api_token
        self.verify_ssl = verify_ssl
        self.siemplify_logger = siemplify_logger
        self.parser = HCLBigFixInventoryParser()
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.sensitive_data = [self.api_token]

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def prepare_request_params(self, **kwargs):
        return {"token": self.api_token, **kwargs}

    def test_connectivity(self):
        """
        Test connectivity
        :return: {void}
        """
        url = self._get_full_url("ping")
        response = self.session.get(url, params=self.prepare_request_params())
        validate_response(response, self.sensitive_data)

    def get_devices(self, custom_fields, ip=None, hostname=None):
        """
        Get devices by entity
        :param custom_fields: {list} List of custom fields to return
        :param ip: {str} IP address
        :param hostname: {str} Hostname
        :return: {list} List of Device objects
        """
        url = self._get_full_url("get_devices")
        payload = {
            "token": self.api_token,
            "columns": [
                "id",
                "bigfix_id",
                "computer_group_id",
                "name",
                "dns_name",
                "ip_address",
                "os",
                "os_type",
                "first_seen",
                "last_seen",
                "is_deleted",
                "deletion_date",
                "is_managed_by_vm_manager",
                "computer_health.agent_version",
                "computer_health.catalog_version",
                "computer_health.is_catalog_scan_successful",
                "computer_health.is_filesys_scan_successful",
                "computer_health.is_idtag_scan_successful",
                "computer_health.is_low_on_disk_space",
                "computer_health.is_missing_prereqs",
                "computer_health.is_out_of_date",
                "computer_health.is_out_of_sync",
                "computer_health.is_package_scan_successful",
                "computer_health.last_scan_attempt",
                "computer_hardware.computer_type",
                "computer_hardware.shared_pool_id",
                "computer_hardware.system_model",
                "computer_hardware.cluster_name",
                "computer_hardware.cluster_cores_count",
                "computer_hardware.partition_cores",
                "computer_hardware.status",
                "computer_hardware.server_id",
                "computer_hardware.server_name",
                "computer_hardware.server_serial_number",
                "computer_hardware.server_type",
                "computer_hardware.server_vendor",
                "computer_hardware.server_model",
                "computer_hardware.node_total_processors",
                "computer_hardware.server_cores",
                "computer_hardware.pvu_per_core",
                "computer_hardware.default_pvu_value",
                "computer_hardware.parent_hostname",
            ]
            + custom_fields,
            "criteria": (
                f'{{"or": [["name", "=", "{hostname}"], '
                f'["dns_name", "=", "{hostname}"]]}}'
                if hostname
                else f'{{"or": [["ip_address", "=", "{ip}"]]}}'
            ),
        }
        response = self.session.get(url, json=payload)
        validate_response(response, self.sensitive_data)
        return self.parser.build_results(
            raw_json=response.json(), method="build_device_obj"
        )
