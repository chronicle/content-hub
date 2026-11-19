from __future__ import annotations
from requests import Session
from typing import List
from urllib.parse import urljoin

from automox.core.AutomoxParser import AutomoxParser
from automox.core.AutomoxUtils import filter_policies, filter_devices_by_field, filter_patches
from soar_sdk.SiemplifyBase import SiemplifyBase

from automox.core.exceptions import AutomoxManagerException, AutomoxAPIError
from automox.core.constants import PAGE_LIMIT
from automox.core.datamodels import Policy, Device, Patch


AUTOMOX_URLS = {
    "ping": "api/orgs",
    "list_policies": "api/policies?limit={limit}&page={page}",
    "list_devices": "api/servers?limit={limit}&page={page}&include_details={include_details}",
    "list_patches": "api/servers/{device_id}/packages?limit={limit}&page={page}",
    "execute_policy": "api/policies/{policy_id}/action",
    "execute_device_command": "api/servers/{id}/queues",
    "queue_data_single": "api/servers/{id}/queues/{command_id}",
    "server_details": "api/servers/{id}?commands=1",
}


class AutomoxManager:
    def __init__(
        self,
        api_root: str,
        api_key: str,
        verify_ssl: bool = True,
        siemplify: SiemplifyBase = None,
    ):
        self.api_root = api_root if api_root[-1] != "/" else api_root[:-1]
        self.siemplify = siemplify

        self.session = Session()
        self.session.verify = verify_ssl
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})

        self.parser = AutomoxParser()

    def __construct_url(self, url_key, **kwargs):
        return urljoin(self.api_root, AUTOMOX_URLS[url_key].format(**kwargs))

    def test_connectivity(self):
        response = self.session.get(self.__construct_url("ping"))
        self.validate_response(response)

    @staticmethod
    def validate_response(response):
        if response.status_code == 400:
            raise AutomoxAPIError(f"Error: {response.json().get('errors')}")
        if response.status_code not in (200, 201):
            raise AutomoxManagerException(
                f"Error: {response.status_code} - {response.text}"
            )

    def get_policies(
        self,
        filter_key: str = None,
        filter_logic: str = None,
        filter_value: str = None,
        max_records_to_return: int = None,
    ) -> List[Policy]:
        page = 0
        policies = []

        while not max_records_to_return or len(policies) < max_records_to_return:
            response = self.session.get(
                self.__construct_url("list_policies", limit=PAGE_LIMIT, page=page)
            )
            self.validate_response(response)
            new_policies = self.parser.build_policies(response.json())
            if not new_policies:
                break

            filtered_policies = filter_policies(
                policies=new_policies,
                filter_key=filter_key,
                filter_logic=filter_logic,
                filter_value=filter_value,
            )
            policies.extend(filtered_policies)

            if len(new_policies) < PAGE_LIMIT:
                break
            page += 1

        return policies[:max_records_to_return]

    def get_devices(
        self,
        filter_value: str = None,
        filter_field: str = None,
        include_details: int = 0,
    ) -> List[Device]:
        page = 0
        devices = []

        while True:
            response = self.session.get(
                self.__construct_url(
                    "list_devices",
                    limit=PAGE_LIMIT,
                    page=page,
                    include_details=include_details,
                ),
                params={"filter[]": filter_value},
            )

            self.validate_response(response)
            new_devices = self.parser.build_devices(response.json())
            if not new_devices:
                break

            filtered_devices = filter_devices_by_field(
                devices=new_devices,
                filter_field=filter_field,
                filter_value=filter_value,
            )

            devices.extend(filtered_devices)

            if len(new_devices) < PAGE_LIMIT:
                break
            page += 1

        return devices

    def get_patches(self, device_id: int, max_patches: int = None) -> List[Patch]:
        page = 0
        patches = []

        while not max_patches or len(patches) < max_patches:
            response = self.session.get(
                self.__construct_url(
                    "list_patches", device_id=device_id, limit=PAGE_LIMIT, page=page
                )
            )
            self.validate_response(response)
            new_patches = self.parser.build_patches(response.json())
            if not new_patches:
                break

            filtered_patches = filter_patches(new_patches)
            patches.extend(filtered_patches)

            if len(new_patches) < PAGE_LIMIT:
                break
            page += 1

        return patches[:max_patches]

    def execute_policy(self, policy_id: int, action: str, server_id: int = None):
        request_body = {"action": action}
        if server_id:
            request_body["serverId"] = server_id
        response = self.session.post(
            self.__construct_url("execute_policy", policy_id=policy_id),
            json=request_body,
        )
        self.validate_response(response)
        return True

    def execute_device_command(self, device_id: int, command: str, args: str = None):
        request_body = {"command_type_name": command}

        if args:
            request_body["args"] = args
        response = self.session.post(
            self.__construct_url("execute_device_command", id=device_id),
            json=request_body,
        )
        self.validate_response(response)
        return True

    def get_queue_data(self, device_id: int):
        response = self.session.get(
            self.__construct_url("execute_device_command", id=device_id)
        )
        self.validate_response(response)

        queue_items = self.parser.build_queue_command_objects(response.json())
        return queue_items

    def get_queue_data_single(self, device_id: int, command_id: int):
        response = self.session.get(
            self.__construct_url(
                "queue_data_single", id=device_id, command_id=command_id
            )
        )
        self.validate_response(response)

        queue_items = self.parser.build_queue_command_objects([response.json()])
        return queue_items[0]
