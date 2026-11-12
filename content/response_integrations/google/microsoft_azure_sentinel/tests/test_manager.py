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

import unittest
import json
import pathlib
from microsoft_azure_sentinel.core.MicrosoftAzureSentinelManager\
import MicrosoftAzureSentinelManager
from microsoft_azure_sentinel.core.exceptions import (
   MicrosoftAzureSentinelManagerError,
   MicrosoftAzureSentinelNotFoundError,
   MicrosoftAzureSentinelTimeoutError,
   MicrosoftAzureSentinelConflictError,
   MicrosoftAzureSentinelPermissionError,
   MicrosoftAzureSentinelUnauthorizedError,
   MicrosoftAzureSentinelBadRequestError,
   MicrosoftAzureSentinelValidationError
)
from unittest.mock import patch, Mock, MagicMock
import requests
from microsoft_azure_sentinel.tests.test_constants import (
   GET_INCIDENTS_BY_FILTER,
   GET_INCIDENT_BY_INCIDENT_NUMBER
)


class TestMicrosoftAzureSentinel(unittest.TestCase):
  """Unit tests for MicrosoftAzureSentinel Integration."""

  def setUp(self) -> None:
    with open(pathlib.Path(__file__).resolve().parent / "config.json", "r", encoding="utf-8") as f:
      data = f.read()
    config = json.loads(data)
    api_root = config.get("Api Root")
    client_id = config.get("Client ID")
    client_secret = config.get("Client Secret")
    tenant_id = config.get("Azure Active Directory ID")
    workspace_id = config.get("Azure Sentinel Workspace Name")
    resource = config.get("Azure Resource Group")
    subscription_id = config.get("Azure Subscription ID")
    login_url = config.get("OAUTH2 Login Endpoint Url")
    verify_ssl = config.get("Verify SSL")
    with patch.object(
      MicrosoftAzureSentinelManager,
      "fetch_token") as mock_fetch_token:
      mock_fetch_token.return_value = ""
      self.manager = MicrosoftAzureSentinelManager(
        api_root=api_root,
        client_id=client_id,
        client_secret=client_secret,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        resource=resource,
        subscription_id=subscription_id,
        login_url=login_url,
        verify_ssl=verify_ssl,
      )

  def test_test_connectivity(self):
    self.manager.test_connectivity = Mock(return_value=True)
    self.assertEqual(
      self.manager.test_connectivity(),
      True,
      "Assertion error: mocking test connectivity failed."
    )

  def test_connectivity_failure(self):
    with patch.object(
      self.manager,
      "test_connectivity"
    ) as mock_test_connectivity:
      mock_test_connectivity.side_effect = (
        MicrosoftAzureSentinelManagerError()
      )
      with self.assertRaises(MicrosoftAzureSentinelManagerError):
        self.manager.test_connectivity()

  @patch("requests.Session.get")
  @patch.object(MicrosoftAzureSentinelManager, "validate_response")
  def test_get_incidents_by_filter(
    self,
    mock_validate_response,
    mock_get
  ):
    mock_validate_response.return_value = None
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = GET_INCIDENTS_BY_FILTER
    mock_get.return_value = mock_response
    incidents = self.manager.get_incidents_by_filter(
      time_frame=3,
      statuses=['New', 'Active', 'Closed'],
      severities=['Informational', 'Low', 'Medium', 'High'],
      limit=0
    )
    incidents = [vars(incident) for incident in incidents]
    self.assertIsInstance(incidents, list)
    self.assertEqual(incidents, [])

  @patch("requests.Session.get")
  @patch.object(MicrosoftAzureSentinelManager, "validate_response")
  def test_get_incidents_by_filter_invalid_status_code_404(
    self,
    mock_validate_response,
    mock_get
  ):
    mock_validate_response.side_effect = (
      MicrosoftAzureSentinelNotFoundError("404 error")
    )
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 404
    mock_response.json.return_value = GET_INCIDENTS_BY_FILTER
    mock_get.return_value = mock_response
    with self.assertRaises(MicrosoftAzureSentinelNotFoundError):
      self.manager.get_incidents_by_filter(
        time_frame=3,
        statuses=['New', 'Active', 'Closed'],
        severities=['Informational', 'Low', 'Medium', 'High'],
        limit=1
    )

  @patch("requests.Session.get")
  @patch.object(MicrosoftAzureSentinelManager, "validate_response")
  def test_get_incidents_by_filter_invalid_status_code_429(
    self,
    mock_validate_response,
    mock_get
  ):
    mock_validate_response.side_effect = (
      MicrosoftAzureSentinelTimeoutError("429 error")
    )
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 429
    mock_response.json.return_value = GET_INCIDENTS_BY_FILTER
    mock_get.return_value = mock_response
    with self.assertRaises(MicrosoftAzureSentinelTimeoutError):
      self.manager.get_incidents_by_filter(
        time_frame=3,
        statuses=['New', 'Active', 'Closed'],
        severities=['Informational', 'Low', 'Medium', 'High'],
        limit=1
      )

  @patch("requests.Session.get")
  @patch.object(MicrosoftAzureSentinelManager, "validate_response")
  def test_get_incidents_by_filter_invalid_status_code_504(
    self,
    mock_validate_response,
    mock_get
  ):
    mock_validate_response.side_effect = (
      MicrosoftAzureSentinelManagerError("504 error")
    )
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 504
    mock_response.json.return_value = GET_INCIDENTS_BY_FILTER
    mock_get.return_value = mock_response
    with self.assertRaises(MicrosoftAzureSentinelManagerError):
      self.manager.get_incidents_by_filter(
        time_frame=3,
        statuses=['New', 'Active', 'Closed'],
        severities=['Informational', 'Low', 'Medium', 'High'],
        limit=1
      )

  @patch("requests.Session.get")
  @patch.object(MicrosoftAzureSentinelManager, "validate_response")
  def test_get_incidents_by_filter_invalid_status_code_409(
    self,
    mock_validate_response,
    mock_get
  ):
    mock_validate_response.side_effect = (
      MicrosoftAzureSentinelConflictError("409 error")
    )
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 409
    mock_response.json.return_value = GET_INCIDENTS_BY_FILTER
    mock_get.return_value = mock_response
    with self.assertRaises(MicrosoftAzureSentinelConflictError):
      self.manager.get_incidents_by_filter(
        time_frame=3,
        statuses=['New', 'Active', 'Closed'],
        severities=['Informational', 'Low', 'Medium', 'High'],
        limit=1
      )

  @patch("requests.Session.get")
  @patch.object(MicrosoftAzureSentinelManager, "validate_response")
  def test_get_incidents_by_filter_invalid_status_code_403(
    self,
    mock_validate_response,
    mock_get
  ):
    mock_validate_response.side_effect = (
      MicrosoftAzureSentinelPermissionError("403 error")
    )
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 403
    mock_response.json.return_value = GET_INCIDENTS_BY_FILTER
    mock_get.return_value = mock_response
    with self.assertRaises(MicrosoftAzureSentinelPermissionError):
      self.manager.get_incidents_by_filter(
        time_frame=3,
        statuses=['New', 'Active', 'Closed'],
        severities=['Informational', 'Low', 'Medium', 'High'],
        limit=1
      )

  @patch("requests.Session.get")
  @patch.object(MicrosoftAzureSentinelManager, "validate_response")
  def test_get_incidents_by_filter_invalid_status_code_401(
    self,
    mock_validate_response,
    mock_get
  ):
    mock_validate_response.side_effect = (
      MicrosoftAzureSentinelUnauthorizedError("401 error")
    )
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 401
    mock_response.json.return_value = GET_INCIDENTS_BY_FILTER
    mock_get.return_value = mock_response
    with self.assertRaises(MicrosoftAzureSentinelUnauthorizedError):
      self.manager.get_incidents_by_filter(
        time_frame=3,
        statuses=['New', 'Active', 'Closed'],
        severities=['Informational', 'Low', 'Medium', 'High'],
        limit=1
      )

  @patch("requests.Session.get")
  @patch.object(MicrosoftAzureSentinelManager, "validate_response")
  def test_get_incidents_by_filter_invalid_status_code_400(
    self,
    mock_validate_response,
    mock_get
  ):
    mock_validate_response.side_effect = (
      MicrosoftAzureSentinelBadRequestError("400 error")
    )
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 400
    mock_response.json.return_value = GET_INCIDENTS_BY_FILTER
    mock_get.return_value = mock_response
    with self.assertRaises(MicrosoftAzureSentinelBadRequestError):
      self.manager.get_incidents_by_filter(
        time_frame=3,
        statuses=['New', 'Active', 'Closed'],
        severities=['Informational', 'Low', 'Medium', 'High'],
        limit=1
      )

  def test_validate_iso8601_duration(self):
    res = self.manager.validate_iso8601_duration("P1DT2H30M")
    self.assertEqual(res, None)

  @patch("isodate.parse_duration")
  def test_validate_iso8601_duration_validation_error(self, mock_parse_duration):
    mock_parse_duration.side_effect = MicrosoftAzureSentinelValidationError()
    with self.assertRaises(MicrosoftAzureSentinelValidationError):
      self.manager.validate_iso8601_duration("P1DT2H30")

  def test_validate_login_response(self):
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 200
    res = self.manager.validate_login_response(mock_response)
    self.assertEqual(res, None)

  def test_validate_login_response_invalid_response(self):
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = MicrosoftAzureSentinelManagerError()
    with self.assertRaises(MicrosoftAzureSentinelManagerError):
      self.manager.validate_login_response(mock_response)

  @patch("requests.Session.get")
  @patch.object(MicrosoftAzureSentinelManager, "validate_response")
  @patch.object(MicrosoftAzureSentinelManager, "_get_incident_by_incident_number")
  def test_get_incidents_by_incident_number(
    self,
    mock_get_incident_by_incident_number,
    mock_validate_response,
    mock_get
  ):
    mock_validate_response.return_value = None
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = GET_INCIDENT_BY_INCIDENT_NUMBER
    mock_get_incident_by_incident_number.return_value = GET_INCIDENT_BY_INCIDENT_NUMBER
    mock_get.return_value = mock_response
    incident = self.manager.get_incident_by_incident_number(incident_number=23)
    self.assertIsInstance(incident, dict)
    self.assertEqual(incident, GET_INCIDENT_BY_INCIDENT_NUMBER)

  @patch("requests.Session.get")
  @patch.object(MicrosoftAzureSentinelManager, "validate_response")
  @patch.object(MicrosoftAzureSentinelManager, "_get_incident_by_incident_number")
  def test_get_incidents_by_incident_number_invalid_status_code_404(
    self,
    mock_get_incident_by_incident_number,
    mock_validate_response,
    mock_get
  ):
    mock_validate_response.side_effect = (
      MicrosoftAzureSentinelNotFoundError("404 error")
    )
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 404
    mock_response.json.return_value = GET_INCIDENT_BY_INCIDENT_NUMBER
    mock_get.return_value = mock_response
    mock_get_incident_by_incident_number.side_effect = (
      MicrosoftAzureSentinelNotFoundError("404 error")
    )
    with self.assertRaises(MicrosoftAzureSentinelNotFoundError):
      self.manager.get_incident_by_incident_number(incident_number=23)

  @patch("requests.Session.get")
  @patch.object(MicrosoftAzureSentinelManager, "validate_response")
  @patch.object(MicrosoftAzureSentinelManager, "_get_incident_by_incident_number")
  def test_get_incidents_by_incident_number_invalid_status_code_401(
    self,
    mock_get_incident_by_incident_number,
    mock_validate_response,
    mock_get
  ):
    mock_validate_response.side_effect = (
      MicrosoftAzureSentinelUnauthorizedError("401 error")
    )
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 401
    mock_response.json.return_value = GET_INCIDENT_BY_INCIDENT_NUMBER
    mock_get.return_value = mock_response
    mock_get_incident_by_incident_number.side_effect = (
      MicrosoftAzureSentinelUnauthorizedError("401 error")
    )
    with self.assertRaises(MicrosoftAzureSentinelUnauthorizedError):
      self.manager.get_incident_by_incident_number(incident_number=23)

  @patch("requests.Session.get")
  @patch.object(MicrosoftAzureSentinelManager, "validate_response")
  @patch.object(MicrosoftAzureSentinelManager, "_get_incident_by_incident_number")
  def test_get_incidents_by_incident_number_invalid_status_code_400(
    self,
    mock_get_incident_by_incident_number,
    mock_validate_response,
    mock_get
  ):
    mock_validate_response.side_effect = (
      MicrosoftAzureSentinelBadRequestError("400 error")
    )
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 400
    mock_response.json.return_value = GET_INCIDENT_BY_INCIDENT_NUMBER
    mock_get.return_value = mock_response
    mock_get_incident_by_incident_number.side_effect = (
      MicrosoftAzureSentinelBadRequestError("400 error")
    )
    with self.assertRaises(MicrosoftAzureSentinelBadRequestError):
      self.manager.get_incident_by_incident_number(incident_number=23)

  @patch("requests.Session.get")
  @patch.object(MicrosoftAzureSentinelManager, "validate_response")
  @patch.object(MicrosoftAzureSentinelManager, "_get_incident_by_incident_number")
  def test_get_incidents_by_incident_number_invalid_status_code_409(
    self,
    mock_get_incident_by_incident_number,
    mock_validate_response,
    mock_get
  ):
    mock_validate_response.side_effect = (
      MicrosoftAzureSentinelConflictError("409 error")
    )
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 401
    mock_response.json.return_value = GET_INCIDENT_BY_INCIDENT_NUMBER
    mock_get.return_value = mock_response
    mock_get_incident_by_incident_number.side_effect = (
      MicrosoftAzureSentinelConflictError("409 error")
    )
    with self.assertRaises(MicrosoftAzureSentinelConflictError):
      self.manager.get_incident_by_incident_number(incident_number=23)

  @patch("requests.Session.get")
  @patch.object(MicrosoftAzureSentinelManager, "validate_response")
  @patch.object(MicrosoftAzureSentinelManager, "_get_incident_by_incident_number")
  def test_get_incidents_by_incident_number_invalid_status_code_504(
    self,
    mock_get_incident_by_incident_number,
    mock_validate_response,
    mock_get
  ):
    mock_validate_response.side_effect = (
      MicrosoftAzureSentinelManagerError("504 error")
    )
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 401
    mock_response.json.return_value = GET_INCIDENT_BY_INCIDENT_NUMBER
    mock_get.return_value = mock_response
    mock_get_incident_by_incident_number.side_effect = (
      MicrosoftAzureSentinelManagerError("504 error")
    )
    with self.assertRaises(MicrosoftAzureSentinelManagerError):
      self.manager.get_incident_by_incident_number(incident_number=23)
