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

import json
import unittest
from unittest.mock import Mock

import pytest
import requests

from microsoft_intune.core.exceptions import (
    MicrosoftIntuneManagerError,
)
from microsoft_intune.core.MicrosoftIntuneManager import (
    MicrosoftIntuneManager,
    SiemplifyLogger,
)
from microsoft_intune.tests.common import CONFIG_PATH, TESTS_DIR


class CustomReponse:
    def json(self)->json:
        return self.result

    def set_json(self,json):
        self.result = json

# Constants
DEVICE_NAME = "CROWDSTRIKEV2"
MAX_RECORDS = 50
FILTER_KEY = "deviceName"
FILTER_LOGIC = "Not Specified"
FILTER_VALUE = ""
LIMIT = 2
FALSE = False
TRUE = True
HOST_NAME = "msintune1"
HOST_ID = "f83f9138"
ACCESS_TOKEN = "access_token"


class TestableMicrosoftIntuneManager(MicrosoftIntuneManager):
    def __init__(
        self,
        azure_ad_endpoint: str,
        microsoft_graph_endpoint: str,
        client_id: str,
        client_secret_value: str,
        azure_ad_id: str,
        verify_ssl: bool,
        logger: SiemplifyLogger | None = None,
    ) -> None:
        self.azure_ad_endpoint = (
            azure_ad_endpoint[:-1]
            if azure_ad_endpoint.endswith("/")
            else azure_ad_endpoint
        )
        self.microsoft_graph_endpoint = microsoft_graph_endpoint
        self.client_id = client_id
        self.client_secret_value = client_secret_value
        self.azure_ad_id = azure_ad_id
        self.verify_ssl = verify_ssl

        self.logger = logger

        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update(
            {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        )


class TestMicrosoftIntuneManager(unittest.TestCase):
    """
    MicrosoftIntuneManager test cases
    """

    def setUp(self) -> None:
        """Initialize a TestableMicrosoftIntuneManager from test config."""
        with CONFIG_PATH.open(encoding="utf-8") as config_file:
            config = json.load(config_file)

        azure_ad_endpoint = config.get("Azure AD endpoint")
        microsoft_graph_endpoint = config.get("Microsoft Graph Endpoint")
        client_id = config.get("Client ID")
        client_secret_value = config.get("Client Secret Value")
        azure_ad_id = config.get("Azure Active Directory ID")
        verify_ssl = bool(config.get("Verify SSL"))
        self.manager = TestableMicrosoftIntuneManager(
            azure_ad_endpoint = azure_ad_endpoint,
            microsoft_graph_endpoint = microsoft_graph_endpoint,
            client_id = client_id,
            client_secret_value = client_secret_value,
            azure_ad_id = azure_ad_id,
            verify_ssl = verify_ssl
        )

    def test_generate_token(self) -> None:
        """
        Generate Token success

        Returns:
            None
        """
        self.manager.generate_token = Mock(
            return_value = ACCESS_TOKEN
        )
        self.assertTrue(self.manager.generate_token(
            HOST_ID
        ))

    def test_list_managed_devices(self) -> None:
        """
        Test List Managed Devices

        Returns:
            None
        """
        response_json = self.mock_get_response('list_managed_device.json')
        custom_response = CustomReponse()
        custom_response.set_json(response_json)
        self.manager.list_managed_devices = Mock(
            return_value = custom_response
        )
        self.assertEqual(
            self.manager.list_managed_devices(
            FILTER_KEY,
            FILTER_LOGIC,
            FILTER_VALUE,
            MAX_RECORDS
            ).json()["@odata.count"],
            LIMIT,
            "Assertion error: mocking list managed devices failed."
        )
        self.assertEqual(
            self.manager.list_managed_devices(
            FILTER_KEY,
            FILTER_LOGIC,
            FILTER_VALUE,
            MAX_RECORDS
            ).json()["value"][0]["deviceName"],
            DEVICE_NAME,
            "Assertion error: mocking list managed devices failed."
        )

    def test_locate_managed_devices_success(self) -> None:
        """
        Locate managed devices success

        Returns:
            None
        """
        self.manager.locate_managed_device = Mock(
            return_value = TRUE
        )
        self.assertTrue(self.manager.locate_managed_device(
            HOST_NAME
        ))

    def test_remote_managed_devices_success(self) -> None:
        """
        Remote managed devices success

        Returns:
            None
        """
        self.manager.remote_lock_managed_device = Mock(
            return_value = TRUE
        )
        self.assertTrue(self.manager.remote_lock_managed_device(
            HOST_ID
        ))

    def test_reset_managed_devices_passcode_success(self) -> None:
        """
        Reset managed devices passcode success

        Returns:
            None
        """
        self.manager.reset_managed_device_passcode = Mock(
            return_value = TRUE
        )
        self.assertTrue(self.manager.reset_managed_device_passcode(
            HOST_ID
        ))

    def test_sync_managed_devices_passcode_success(self) -> None:
        """
        Sync managed devices success

        Returns:
            None
        """
        self.manager.sync_managed_device = Mock(
            return_value = TRUE
        )
        self.assertTrue(self.manager.sync_managed_device(
            HOST_ID
        ))

    def test_wipe_managed_devices_passcode_success(self) -> None:
        """
        Wipe managed devices success

        Returns:
            None
        """
        self.manager.wipe_managed_device = Mock(
            return_value = TRUE
        )
        self.assertTrue(self.manager.wipe_managed_device(
            HOST_ID,
            FALSE,
            FALSE,
            FALSE,
            ""

        ))

    @pytest.mark.usefixtures("mock_list_devices_to_raise_manager_error")
    def test_list_managed_devices_failure(self) -> None:
        """
        Test list managed devices failure

        Returns:
            None
        """
        with pytest.raises(MicrosoftIntuneManagerError):
            self.manager.list_managed_devices()

    @pytest.mark.usefixtures("mock_locate_devices_to_raise_manager_error")
    def test_locate_managed_devices_failure(self) -> None:
        """
        Test locate managed devices failure

        Returns:
            None
        """
        with pytest.raises(MicrosoftIntuneManagerError):
            self.manager.locate_managed_device()

    @pytest.mark.usefixtures("mock_reset_devices_passcode_to_raise_manager_error")
    def test_reset_managed_devices_failure(self) -> None:
        """
        Test reset managed devices passcode failure

        Returns:
            None
        """
        with pytest.raises(MicrosoftIntuneManagerError):
            self.manager.reset_managed_device_passcode()

    @pytest.mark.usefixtures("mock_remote_devices_to_raise_manager_error")
    def test_remote_managed_devices_failure(self) -> None:
        """
        Test remote managed devices failure

        Returns:
            None
        """
        with pytest.raises(MicrosoftIntuneManagerError):
            self.manager.remote_lock_managed_device()

    @pytest.mark.usefixtures("mock_sync_devices_to_raise_manager_error")
    def test_sync_managed_devices_failure(self) -> None:
        """
        Test sync managed devices failure

        Returns:
            None
        """
        with pytest.raises(MicrosoftIntuneManagerError):
            self.manager.sync_managed_device()

    @pytest.mark.usefixtures("mock_wipe_devices_to_raise_manager_error")
    def test_wipe_managed_devices_failure(self) -> None:
        """
        Test wipe managed devices failure

        Returns:
            None
        """
        with pytest.raises(MicrosoftIntuneManagerError):
            self.manager.wipe_managed_device()

    def mock_get_response(self,file_name) -> json:
        """
            Fetch mock json file

            Returns:
                json
            """
        with (TESTS_DIR / file_name).open(encoding="utf-8") as response_file:
            return json.load(response_file)
