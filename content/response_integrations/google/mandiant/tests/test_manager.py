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

"""Unit tests for Mandiant Integration."""
import json
import logging
import os
import unittest
from unittest.mock import Mock, patch
from mandiant.core.MandiantManager import MandiantManager

# Constants
LIMIT = 5

ACTION_MOCK_DATA = json.load(
    open(
        os.path.join(os.path.dirname(__file__), "mock_data/actor_details.json")
    )
)
MALWARE_MOCK_DATA = json.load(
    open(
        os.path.join(os.path.dirname(__file__),
                     "mock_data/malware_details.json")
    )
)
VULERABILITY_MOCK_DATA = json.load(
    open(
        os.path.join(os.path.dirname(__file__),
                     "mock_data/vulerability_details.json")
    )
)
INDICATOR_MOCK_DATA = json.load(
    open(
        os.path.join(os.path.dirname(__file__),
                     "mock_data/indicator_details.json")
    )
)
THREAT_ACTOR_INDICATOR_MOCK_DATA = json.load(
    open(
        os.path.join(os.path.dirname(__file__),
                     "mock_data/threat_actor_indicators.json")
    )
)
MALWARE_INDICATORS_MOCK_DATA = json.load(
    open(
        os.path.join(os.path.dirname(__file__),
                     "mock_data/malware_indicators.json")
    )
)

GET_INDICATOR_DETAILS = INDICATOR_MOCK_DATA.get("raw_data")
GET_ACTOR_DETAILS = ACTION_MOCK_DATA.get("raw_data")
GET_VULERABILITY_DETAILS = VULERABILITY_MOCK_DATA.get("raw_data")
GET_MALWARE_DETAILS = MALWARE_MOCK_DATA.get("raw_data")
GET_THREAT_ACTOR_IDENTIFIER = ACTION_MOCK_DATA.get("raw_data")["id"]
GET_MALWARE_IDENTIFIER = MALWARE_MOCK_DATA.get("raw_data")["id"]


class TestMandiantManager(unittest.TestCase):
    """Unit tests for Mandiant Integration."""

    def setUp(self) -> None:
        self.logger = logging.getLogger(__name__)
        with open(os.path.join(os.path.dirname(__file__), "config.json"), "r") as f:
            data = f.read()

        config = json.loads(data)

        ui_root = config.get("UI Root")
        api_root = config.get("API Root")
        client_id = config.get("Client ID")
        client_secret = config.get("Client Secret")
        verify_ssl = config.get("Verify SSL")

        with patch.object(
            MandiantManager,"_generate_token")as mock_generate_token:
            mock_generate_token.return_value = ""
            self.manager = MandiantManager(
                ui_root,
                api_root,
                client_id,
                client_secret,
                verify_ssl
            )

    def test_test_connectivity(self) -> None:
        """Mocking test connectivity for the API.

        Returns:
            None
        """
        self.manager.test_connectivity = Mock(return_value=True)
        self.assertEqual(
            self.manager.test_connectivity(),
            True,
            "Assertion error: mocking test connectivity failed."
        )

    def test_get_indicator_details(self):
        self.manager.get_indicator_details = Mock(
            return_value=GET_INDICATOR_DETAILS
            )
        self.assertEqual(
            self.manager.get_indicator_details(),
            GET_INDICATOR_DETAILS
        )

    def test_get_vulerability_details(self):
        self.manager.get_vulnerability_details = Mock(
            return_value=GET_VULERABILITY_DETAILS
            )
        self.assertEqual(
            self.manager.get_vulnerability_details(),
            GET_VULERABILITY_DETAILS
        )

    def test_get_actor_details(self):
        self.manager.get_actor_details = Mock(
            return_value=GET_ACTOR_DETAILS
            )
        self.assertEqual(
            self.manager.get_actor_details(),
            GET_ACTOR_DETAILS
        )

    def test_get_malware_details(self):
        self.manager.get_malware_details = Mock(
            return_value=GET_MALWARE_DETAILS
            )
        self.assertEqual(
            self.manager.get_malware_details(),
            GET_MALWARE_DETAILS
        )

    def test_get_threat_actor_indicators(self):
        self.manager.get_threat_actor_indicators = Mock(
            return_value=THREAT_ACTOR_INDICATOR_MOCK_DATA
            )
        self.assertEqual(
            self.manager.get_threat_actor_indicators(
            GET_THREAT_ACTOR_IDENTIFIER, LIMIT),
            THREAT_ACTOR_INDICATOR_MOCK_DATA
        )

    def test_get_malware_indicators(self):
        self.manager.get_malware_indicators = Mock(
            return_value=MALWARE_INDICATORS_MOCK_DATA
            )
        self.assertEqual(
            self.manager.get_malware_indicators(GET_MALWARE_IDENTIFIER, LIMIT),
            MALWARE_INDICATORS_MOCK_DATA
        )