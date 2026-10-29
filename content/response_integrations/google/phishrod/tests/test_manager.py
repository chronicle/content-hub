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
import pathlib
import unittest
from unittest.mock import Mock, patch
import pytest
from phishrod.core.datamodels import (
    MarkIncidentData,
    UpdateIncidentData
)
from phishrod.core.PhishrodExceptions import PhishrodException
from phishrod.core.PhishrodManager import PhishrodManager

Logger = Mock

#Constants

MARK_INCIDENT_DATA = {
    "code": "200",
    "status": "Reported Email Marked as Spam by Analyst"
}

ALREADY_MARK_INCIDENT_DATA = {
    "code": "200",
    "status": "Incident status has already been updated before."
}

UPDATED_INCIDENT = {
    "statusMarked": True,
    "message": "Incident status has been marked successfully."
}

ALREADY_UPDATED_INCIDENT = {
    "statusMarked": False,
    "message": "Incident status is already marked."
}
FAILED_TO_UPDATE_INCIDENT = {
    "statusMarked": False,
    "message": "No reported incident found against provided incident number."
}

class TestPhishrodManager(unittest.TestCase):
    """
    PhishrodManager test cases
    """

    def setUp(self) -> None:
        config_path = pathlib.Path(__file__).parent / "config.json"
        with open(config_path, "r", encoding="utf-8") as config_file:
            config = json.load(config_file)

        api_root = config.get("API Root")
        api_key = config.get("API Key")
        client_id = config.get("Client ID")
        username = config.get("Username")
        password = config.get("Password")
        verify_ssl = config.get("Verify SSL")
        self.manager = PhishrodManager(
            api_root = api_root,
            api_key = api_key,
            client_id = client_id,
            username = username,
            password = password,
            verify_ssl = verify_ssl,
            siemplify_logger = Logger(),
        )

    def test_connectivity_success(self) -> None:
        """
        Test connectivity success

        Returns:
            None
        """
        mock_get_request = Mock()
        mock_get_request.json.return_value = {}

        with patch.object(self.manager.session, 'get', return_value=mock_get_request):
            self.assertTrue(self.manager.test_connectivity())

    @pytest.mark.usefixtures("mock_test_connectivity_to_raise_manager_error")
    def test_connectivity_failure(self) -> None:
        """
        Test connectivity failure

        Returns:
            None
        """
        with pytest.raises(PhishrodException):
            self.manager.test_connectivity()

    def test_get_incidents(self) -> None:
        """
        Test get incidents

        Returns:
            None
        """
        mock_get_request = Mock()
        mock_get_request.json.return_value = {
            'incidents': [
                {
                    'reportedBy': [
                        {
                            'reportDateTime': '2023-09-19 17:34:17.123456'
                        }
                    ]
                }
            ]
        }
        with patch.object(self.manager.session, 'get', return_value=mock_get_request):
            incidents = self.manager.get_incidents()
            for incident in incidents:
                self.assertEqual(type(incident).__name__, 'Incident')

    @pytest.mark.usefixtures("mock_get_incidents_to_raise_manager_error")
    def test_get_incidents_failure(self) -> None:
        """
        Test get incidents failure

        Returns:
            None
        """
        with pytest.raises(PhishrodException):
            self.manager.get_incidents()

    def test_mark_incident(self) -> None:
        """
        Test mark incident

        Returns:
            None
        """
        mark_incident = MarkIncidentData(
                raw_data = MARK_INCIDENT_DATA,
                code = MARK_INCIDENT_DATA.get('code'),
                status = MARK_INCIDENT_DATA.get('status')
            )
        self.manager.mark_incident = Mock(
            return_value = mark_incident
        )
        self.assertEqual(
            self.manager.mark_incident().status,
            "Reported Email Marked as Spam by Analyst",
            "Assertion error: mocking mark incident failed."
        )
        self.assertEqual(
            self.manager.mark_incident().code,
            "200",
            "Assertion error: mocking mark incident failed."
        )

    def test_already_mark_incident(self) -> None:
        """
        Test already mark incident

        Returns:
            None
        """
        mark_incident = MarkIncidentData(
                raw_data = ALREADY_MARK_INCIDENT_DATA,
                code = ALREADY_MARK_INCIDENT_DATA.get('code'),
                status = ALREADY_MARK_INCIDENT_DATA.get('status')
            )
        self.manager.mark_incident = Mock(
            return_value = mark_incident
        )
        self.assertEqual(
            self.manager.mark_incident().status,
            "Incident status has already been updated before.",
            "Assertion error: mocking already mark incident failed."
        )
        self.assertEqual(
            self.manager.mark_incident().code,
            "200",
            "Assertion error: mocking already mark incident failed."
        )

    def test_updated_incident(self) -> None:
        """
        Test updated incident

        Returns:
            None
        """
        update_incident = UpdateIncidentData(
                raw_data = UPDATED_INCIDENT,
                status_marked = UPDATED_INCIDENT.get('statusMarked'),
                message = UPDATED_INCIDENT.get('message')
            )
        self.manager.update_incident = Mock(
            return_value = update_incident
        )
        self.assertEqual(
            self.manager.update_incident().message,
            "Incident status has been marked successfully.",
            "Assertion error: mocking already update incident failed."
        )
        self.assertTrue(
            self.manager.update_incident().status_marked,
            "Assertion error: mocking already update incident failed."
        )

    def test_already_updated_incident(self) -> None:
        """
        Test already updated incident

        Returns:
            None
        """
        update_incident = UpdateIncidentData(
                raw_data = ALREADY_UPDATED_INCIDENT,
                status_marked = ALREADY_UPDATED_INCIDENT.get('statusMarked'),
                message = ALREADY_UPDATED_INCIDENT.get('message')
            )
        self.manager.update_incident = Mock(
            return_value = update_incident
        )
        self.assertEqual(
            self.manager.update_incident().message,
            "Incident status is already marked.",
            "Assertion error: mocking already update incident failed."
        )
        self.assertFalse(
            self.manager.update_incident().status_marked,
            "Assertion error: mocking already update incident failed."
        )

    def test_failed_to_updated_incident(self) -> None:
        """
        Test failed to updated incident

        Returns:
            None
        """
        update_incident = UpdateIncidentData(
                raw_data = FAILED_TO_UPDATE_INCIDENT,
                status_marked = FAILED_TO_UPDATE_INCIDENT.get('statusMarked'),
                message = FAILED_TO_UPDATE_INCIDENT.get('message')
            )
        self.manager.update_incident = Mock(
            return_value=update_incident
        )
        self.assertEqual(
            self.manager.update_incident().message,
            "No reported incident found against provided incident number.",
            "Assertion error: mocking failed to update incident failed."
        )
        self.assertFalse(
            self.manager.update_incident().status_marked,
            "Assertion error: mocking already update incident failed."
        )

    @pytest.mark.usefixtures("mock_mark_incident_to_raise_manager_error")
    def test_mark_incident_failure(self) -> None:
        """
        Test mark incident failure

        Returns:
            None
        """
        with pytest.raises(PhishrodException):
            self.manager.mark_incident()

    @pytest.mark.usefixtures("mock_update_incident_to_raise_manager_error")
    def test_update_incident_failure(self) -> None:
        """
        Test update incident failure

        Returns:
            None
        """
        with pytest.raises(PhishrodException):
            self.manager.update_incident()
