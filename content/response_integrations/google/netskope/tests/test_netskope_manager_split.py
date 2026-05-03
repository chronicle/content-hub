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
import datetime
from itertools import islice
import json
import os
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

from datamodels import Client

import requests
import netskopeManager as NM
from NetskopeManager import NetskopeManager
from NetskopeManagerV2 import NetskopeManagerV2
from NetskopeManagerFactory import NetskopeManagerFactory
from NetskopeAuth import NetskopeV1Auth, NetskopeV2BearerAuth, NetskopeV2OAuth

# Load mock data
DIR_PATH = os.path.dirname(os.path.realpath(__file__))
MOCK_DATA_PATH = os.path.join(DIR_PATH, "mock_data.json")

with open(MOCK_DATA_PATH, "r", encoding="utf-8") as f:
    MOCK_DATA = json.load(f)


class TestNetskopeManager:
    """Unit tests for NetskopeManager v1."""

    def test_get_clients(self) -> None:
        """Test getting clients in V1.

        Returns:
            None
        """
        with patch("requests.Session.request") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "status": "success",
                "data": MOCK_DATA["clients_v1"]["data"],
            }
            mock_get.return_value = mock_response

            manager = NetskopeManager("https://test.com", "api_key")
            clients_gen = manager.get_clients(limit=1)
            clients = list(islice(clients_gen, 1))

            assert len(clients) == 1
            assert clients[0].device_id == "Chromebook-b08e475425b09c11"

    def test_get_clients_pagination_simulation(self) -> None:
        """Test getting clients with simulated pagination in V1."""

        old_max_limit = NM.MAX_CLIENTS_LIMIT_V1
        NM.MAX_CLIENTS_LIMIT_V1 = 2

        try:
            with patch("requests.Session.request") as mock_request:
                mock_response_1 = MagicMock()
                mock_response_1.json.return_value = {
                    "status": "success",
                    "data": [{"device_id": "1"}, {"device_id": "2"}],
                }
                mock_response_2 = MagicMock()
                mock_response_2.json.return_value = {
                    "status": "success",
                    "data": [{"device_id": "3"}, {"device_id": "4"}],
                }
                mock_response_3 = MagicMock()
                mock_response_3.json.return_value = {
                    "status": "success",
                    "data": [{"device_id": "5"}],
                }

                mock_request.side_effect = [
                    mock_response_1,
                    mock_response_2,
                    mock_response_3,
                ]

                manager = NetskopeManager("https://test.com", "api_key")
                clients_gen = manager.get_clients(limit=6)
                clients = list(clients_gen)

                assert len(clients) == 5
                assert mock_request.call_count == 3

                # Check call parameters
                kwargs_1 = mock_request.call_args_list[0].kwargs
                assert kwargs_1["params"]["limit"] == 2
                assert kwargs_1["params"]["skip"] == 0

                kwargs_2 = mock_request.call_args_list[1].kwargs
                assert kwargs_2["params"]["limit"] == 2
                assert kwargs_2["params"]["skip"] == 2

                kwargs_3 = mock_request.call_args_list[2].kwargs
                assert kwargs_3["params"]["limit"] == 2
                assert kwargs_3["params"]["skip"] == 4
        finally:
            NM.MAX_CLIENTS_LIMIT_V1 = old_max_limit

    def test_v1_auth_duplicate_params(self) -> None:
        """Test that NetskopeV1Auth preserves duplicate query parameters."""
        auth = NetskopeV1Auth("test_token")
        request = requests.Request(
            "GET", "https://test.com/api/v1/clients?filter=a&filter=b"
        ).prepare()

        auth(request)

        # The URL should contain both filters and the token
        assert "filter=a" in request.url
        assert "filter=b" in request.url
        assert "token=test_token" in request.url

    def test_get_clients_pagination(self) -> None:
        """Test getting clients with pagination in V1."""
        with patch("requests.Session.request") as mock_get:
            mock_response_1 = MagicMock()
            mock_response_1.json.return_value = {
                "status": "success",
                "data": [
                    {"attributes": {"_id": "device_1"}},
                    {"attributes": {"_id": "device_2"}},
                ],
            }
            mock_response_2 = MagicMock()
            mock_response_2.json.return_value = {
                "status": "success",
                "data": [{"attributes": {"_id": "device_3"}}],
            }

            mock_get.side_effect = [mock_response_1, mock_response_2]

            manager = NetskopeManager("https://test.com", "api_key")
            with patch("NetskopeManager.MAX_CLIENTS_LIMIT_V1", 2):
                clients_gen = manager.get_clients()
                clients = list(clients_gen)

                assert len(clients) == 3
                assert clients[0].device_id == "device_1"
                assert clients[-1].device_id == "device_3"
                assert mock_get.call_count == 2


class TestNetskopeManagerV2:
    """Unit tests for NetskopeManagerV2."""

    def test_get_events(self) -> None:
        """Test getting events in V2.

        Returns:
            None
        """
        with patch("requests.Session.request") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "ok": 1,
                "result": MOCK_DATA["events_v2"]["result"],
            }
            mock_get.return_value = mock_response

            manager = NetskopeManagerV2("https://test.com", "v2_token")
            events_gen = manager.get_events(limit=1)
            events = list(islice(events_gen, 1))

            assert len(events) == 1
            assert events[0]["_id"] == "event_1"

    def test_oauth_get_events(self) -> None:
        """Test getting events with OAuth in V2.

        Returns:
            None
        """
        with patch("requests.Session.request") as mock_request:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {
                "oAuth2AccessToken": "new_generated_token",
                "expiryTime": "2026-04-07T09:09:04.000Z",
            }

            mock_data_response = MagicMock()
            mock_data_response.json.return_value = {
                "ok": 1,
                "result": MOCK_DATA["events_v2"]["result"],
            }

            def request_side_effect(*args, **kwargs):
                url = args[1] if len(args) > 1 else kwargs.get("url", "")
                if "token/generate" in url:
                    return mock_token_response
                return mock_data_response

            mock_request.side_effect = request_side_effect

            manager = NetskopeManagerV2(
                "https://test.com", client_id="client_id", client_secret="client_secret"
            )
            # Manually trigger token generation as mocking
            # requests.Session.request bypasses auth handler
            manager.session.auth._generate_access_token()  # pylint: disable=protected-access

            events_gen = manager.get_events(limit=1)
            events = list(islice(events_gen, 1))

            assert len(events) == 1
            assert events[0]["_id"] == "event_1"

            # Check if token was generated
            assert manager.session.auth.generated_token == "new_generated_token"

    def test_auth_priority(self) -> None:
        """Test that Client ID/Secret are prioritized over legacy token."""
        with patch("requests.Session.request") as mock_request:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {
                "oAuth2AccessToken": "new_generated_token",
                "expiryTime": "2026-04-07T09:09:04.000Z",
            }

            mock_data_response = MagicMock()
            mock_data_response.json.return_value = {
                "ok": 1,
                "result": MOCK_DATA["events_v2"]["result"],
            }

            def request_side_effect(*args, **kwargs):
                url = args[1] if len(args) > 1 else kwargs.get("url", "")
                if "token/generate" in url:
                    return mock_token_response
                return mock_data_response

            mock_request.side_effect = request_side_effect

            manager = NetskopeManagerV2(
                "https://test.com",
                v2_api_token="legacy_token",
                client_id="client_id",
                client_secret="client_secret",
            )
            # Manually trigger token generation as mocking
            # requests.Session.request bypasses auth handler
            manager.session.auth._generate_access_token()  # pylint: disable=protected-access

            # Check if token was generated (overwriting the legacy token)
            assert manager.session.auth.generated_token == "new_generated_token"

    def test_test_connectivity(self) -> None:
        """Test test_connectivity in V2.

        Returns:
            None
        """
        with patch("requests.Session.request") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "ok": 1,
                "result": MOCK_DATA["alerts_v2"]["result"],
            }
            mock_get.return_value = mock_response

            manager = NetskopeManagerV2("https://test.com", "v2_token")
            result = manager.test_connectivity()

            assert result is True

    def test_get_clients(self) -> None:
        """Test getting clients in V2.

        Returns:
            None
        """
        with patch("requests.Session.request") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "ok": 1,
                "result": MOCK_DATA["clients_v2"]["result"],
            }
            mock_get.return_value = mock_response

            manager = NetskopeManagerV2("https://test.com", "v2_token")
            clients_gen = manager.get_clients(limit=1)
            clients = list(islice(clients_gen, 1))

            assert len(clients) == 1
            assert clients[0].device_id == "Chromebook-b08e475425b09c11"

    def test_get_clients_host_info_null(self) -> None:
        """Test getting clients when host_info is null in V2."""
        with patch("requests.Session.request") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "ok": 1,
                "result": [
                    {
                        "device_id": "device_1",
                        "user_info": {"username": "user1"},
                        "host_info": None,
                    }
                ],
            }
            mock_get.return_value = mock_response

            manager: NetskopeManagerV2 = NetskopeManagerV2(
                "https://test.com", "v2_token"
            )
            clients_gen: Generator[Client, None, None] = manager.get_clients(limit=1)
            clients: list[Client] = list(islice(clients_gen, 1))

            assert len(clients) == 1
            assert clients[0].device_id == "device_1"
            assert clients[0].os is None

    def test_get_quarantined_files(self) -> None:
        """Test getting quarantined files in V2.

        Returns:
            None
        """
        with patch("requests.Session.request") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "ok": 1,
                "quarantineIncidents": MOCK_DATA["quarantine_files_v2"][
                    "quarantineIncidents"
                ],
            }
            mock_get.return_value = mock_response

            manager = NetskopeManagerV2("https://test.com", "v2_token")
            files_gen = manager.get_quarantined_files(limit=1)
            files = list(files_gen)

            assert len(files) == 1
            assert files[0]["id"] == "quarantineIncident1"

    def test_block_file(self) -> None:
        """Test blocking file in V2.

        Returns:
            None
        """
        with patch("requests.Session.request") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            manager = NetskopeManagerV2("https://test.com", "v2_token")
            result = manager.block_file("file_1")

            assert result is True

    def test_allow_file(self) -> None:
        """Test allowing file in V2.

        Returns:
            None
        """
        with patch("requests.Session.request") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            manager = NetskopeManagerV2("https://test.com", "v2_token")
            result = manager.allow_file("file_1")

            assert result is True

    def test_download_file(self) -> None:
        """Test downloading file in V2.

        Returns:
            None
        """
        with patch("requests.Session.request") as mock_get:
            mock_response = MagicMock()
            mock_response.content = b"content"
            mock_get.return_value = mock_response

            manager = NetskopeManagerV2("https://test.com", "v2_token")
            result = manager.download_file("app", "instance", "file_1")

            assert result == b"content"

    def test_get_quarantined_files_pagination(self) -> None:
        """Test getting quarantined files with pagination in V2.

        Returns:
            None
        """
        with patch("requests.Session.request") as mock_get:
            mock_response_1 = MagicMock()
            mock_response_1.json.return_value = {
                "ok": 1,
                "quarantineIncidents": [
                    {"id": f"quarantineIncident_{i}"} for i in range(100)
                ],
            }
            mock_response_2 = MagicMock()
            mock_response_2.json.return_value = {
                "ok": 1,
                "quarantineIncidents": [
                    {"id": f"quarantineIncident_{i}"} for i in range(100, 150)
                ],
            }

            mock_get.side_effect = [mock_response_1, mock_response_2]

            manager = NetskopeManagerV2("https://test.com", "v2_token")
            files_gen = manager.get_quarantined_files(limit=150)
            files = list(files_gen)

            assert len(files) == 150
            assert files[0]["id"] == "quarantineIncident_0"
            assert files[-1]["id"] == "quarantineIncident_149"
            assert mock_get.call_count == 2

    def test_get_quarantined_files_auto_endtime(self) -> None:
        """Test getting quarantined files with auto endtime in V2.

        Returns:
            None
        """
        with patch("requests.Session.request") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "ok": 1,
                "quarantineIncidents": MOCK_DATA["quarantine_files_v2"][
                    "quarantineIncidents"
                ],
            }
            mock_get.return_value = mock_response

            manager = NetskopeManagerV2("https://test.com", "v2_token")
            files_gen = manager.get_quarantined_files(start_time=1769496347, limit=1)
            files = list(islice(files_gen, 1))

            assert len(files) == 1
            _, kwargs = mock_get.call_args
            params = kwargs.get("params")
            assert params is not None
            assert "starttime" in params
            assert "endtime" in params
            assert params["starttime"] == 1769496347
            assert params["endtime"] is not None

    def test_get_events_pagination(self) -> None:
        """Test getting events with pagination in V2."""
        with patch("requests.Session.request") as mock_get:
            mock_response_1 = MagicMock()
            mock_response_1.json.return_value = {
                "ok": 1,
                "result": [{"_id": "event_1"}, {"_id": "event_2"}],
            }
            mock_response_2 = MagicMock()
            mock_response_2.json.return_value = {
                "ok": 1,
                "result": [{"_id": "event_3"}],
            }

            mock_get.side_effect = [mock_response_1, mock_response_2]

            manager = NetskopeManagerV2("https://test.com", "v2_token")
            with patch("NetskopeManagerV2.MAX_EVENTS_LIMIT_V2", 2):
                events_gen = manager.get_events()
                events = list(events_gen)

                assert len(events) == 3
                assert events[0]["_id"] == "event_1"
                assert events[-1]["_id"] == "event_3"
                assert mock_get.call_count == 2

    def test_get_clients_pagination_v2(self) -> None:
        """Test getting clients with pagination in V2."""
        with patch("requests.Session.request") as mock_get:
            mock_response_1 = MagicMock()
            mock_response_1.json.return_value = {
                "ok": 1,
                "result": [{"device_id": "device_1"}, {"device_id": "device_2"}],
            }
            mock_response_2 = MagicMock()
            mock_response_2.json.return_value = {
                "ok": 1,
                "result": [{"device_id": "device_3"}],
            }

            mock_get.side_effect = [mock_response_1, mock_response_2]

            manager = NetskopeManagerV2("https://test.com", "v2_token")
            with patch("NetskopeManagerV2.MAX_CLIENTS_LIMIT_V2", 2):
                clients_gen = manager.get_clients()
                clients = list(clients_gen)

                assert len(clients) == 3
                assert clients[0].device_id == "device_1"
                assert clients[-1].device_id == "device_3"
                assert mock_get.call_count == 2

    def test_get_alerts(self) -> None:
        """Test getting alerts in V2."""
        with patch("requests.Session.request") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "ok": 1,
                "result": [{"_id": "alert_1"}],
            }
            mock_get.return_value = mock_response

            manager = NetskopeManagerV2("https://test.com", "v2_token")
            alerts_gen = manager.get_alerts(limit=1)
            alerts = list(islice(alerts_gen, 1))

            assert len(alerts) == 1
            assert alerts[0]["_id"] == "alert_1"

    def test_get_alerts_pagination(self) -> None:
        """Test getting alerts with pagination in V2."""
        with patch("requests.Session.request") as mock_get:
            mock_response_1 = MagicMock()
            mock_response_1.json.return_value = {
                "ok": 1,
                "result": [{"_id": "alert_1"}, {"_id": "alert_2"}],
            }
            mock_response_2 = MagicMock()
            mock_response_2.json.return_value = {
                "ok": 1,
                "result": [{"_id": "alert_3"}],
            }

            mock_get.side_effect = [mock_response_1, mock_response_2]

            manager = NetskopeManagerV2("https://test.com", "v2_token")
            with patch("NetskopeManagerV2.MAX_EVENTS_LIMIT_V2", 2):
                alerts_gen = manager.get_alerts()
                alerts = list(alerts_gen)

                assert len(alerts) == 3
                assert alerts[0]["_id"] == "alert_1"
                assert alerts[-1]["_id"] == "alert_3"
                assert mock_get.call_count == 2


class TestNetskopeManagerFactory:
    """Unit tests for NetskopeManagerFactory."""

    def test_get_v1(self, mock_siemplify: MagicMock) -> None:
        """Test getting V1 manager from factory.

        Args:
            siemplify_mock (MagicMock): mock siemplify object.

        Returns:
            None
        """
        with patch("NetskopeManagerFactory.extract_script_param") as mock_extract:

            def side_effect(*_: Any, **kwargs: Any) -> Any:
                param_name = kwargs.get("param_name")
                if param_name == "Api Root":
                    return "https://test.com"
                if param_name == "Verify SSL":
                    return True
                if param_name == "V1 Api Key":
                    return "v1_key"
                return None

            mock_extract.side_effect = side_effect

            manager = NetskopeManagerFactory.get_manager(
                mock_siemplify, api_version="v1"
            )
            assert isinstance(manager, NetskopeManager)

    def test_get_v2(self, mock_siemplify: MagicMock) -> None:
        """Test getting V2 manager from factory.

        Args:
            siemplify_mock (MagicMock): mock siemplify object.

        Returns:
            None
        """
        with patch("NetskopeManagerFactory.extract_script_param") as mock_extract:

            def side_effect(*_: Any, **kwargs: Any) -> Any:
                param_name = kwargs.get("param_name")
                if param_name == "Api Root":
                    return "https://test.com"
                if param_name == "Verify SSL":
                    return True
                if param_name == "V2 Api Key":
                    return "v2_key"
                return None

            mock_extract.side_effect = side_effect

            manager = NetskopeManagerFactory.get_manager(
                mock_siemplify, api_version="v2"
            )
            assert isinstance(manager, NetskopeManagerV2)

    def test_get_v2_oauth(self, mock_siemplify: MagicMock) -> None:
        """Test getting V2 manager with OAuth from factory.

        Args:
            siemplify_mock (MagicMock): mock siemplify object.

        Returns:
            None
        """
        with patch(
            "NetskopeManagerFactory.extract_script_param"
        ) as mock_extract, patch("requests.Session.request") as mock_request:

            def side_effect(*_: Any, **kwargs: Any) -> Any:
                param_name = kwargs.get("param_name")
                if param_name == "Api Root":
                    return "https://test.com"
                if param_name == "Verify SSL":
                    return True
                if param_name == "Client ID":
                    return "client_id"
                if param_name == "Client Secret":
                    return "client_secret"
                return None

            mock_extract.side_effect = side_effect

            mock_response = MagicMock()
            mock_response.json.return_value = {"oAuth2AccessToken": "test_token"}
            mock_request.return_value = mock_response

            manager = NetskopeManagerFactory.get_manager(
                mock_siemplify, api_version="v2"
            )
            assert isinstance(manager, NetskopeManagerV2)
            assert manager.session.auth.client_id == "client_id"
            assert manager.session.auth.client_secret == "client_secret"


class TestNetskopeAuthV2:
    """Unit tests for Netskope V2 auth classes."""

    def test_auth_generates_token_initially(self) -> None:
        """Test that NetskopeV2OAuth generates token on first call."""
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "oAuth2AccessToken": "new_oauth_token",
                "expiryTime": "2026-04-07T09:09:04.000Z",
            }
            mock_post.return_value = mock_response

            auth = NetskopeV2OAuth(
                api_root="https://test.com",
                client_id="client_id",
                client_secret="client_secret",
            )

            request = requests.PreparedRequest()
            request.url = "https://test.com/api/v2/events"
            request.headers = {}

            auth(request)

            assert mock_post.called
            assert request.headers["Authorization"] == "Bearer new_oauth_token"

    def test_auth_fallback_static(self) -> None:
        """Test that NetskopeV2BearerAuth uses static token."""
        auth = NetskopeV2BearerAuth(access_token="static_token")
        request = requests.PreparedRequest()
        request.url = "https://test.com/api/v2/events"
        request.headers = {}

        auth(request)

        assert request.headers["Authorization"] == "Bearer static_token"

    def test_auth_token_expired(self) -> None:
        """Test that token is refreshed if expired in NetskopeV2OAuth."""
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "oAuth2AccessToken": "new_oauth_token",
                "expiryTime": (
                    datetime.datetime.now(datetime.timezone.utc)
                    + datetime.timedelta(hours=1)
                ).isoformat(),
            }
            mock_post.return_value = mock_response

            auth = NetskopeV2OAuth(
                api_root="https://test.com",
                client_id="client_id",
                client_secret="client_secret",
            )

            # Set expired token
            auth.generated_token = "old_token"
            auth.expiry_time = datetime.datetime.now(
                datetime.timezone.utc
            ) - datetime.timedelta(minutes=5)

            request = requests.PreparedRequest()
            request.url = "https://test.com/api/v2/events"
            request.headers = {}

            auth(request)

            assert mock_post.called
            assert request.headers["Authorization"] == "Bearer new_oauth_token"

    def test_auth_token_not_expired(self) -> None:
        """Test that token is NOT refreshed if not expired in NetskopeV2OAuth."""
        with patch("requests.post") as mock_post:
            auth = NetskopeV2OAuth(
                api_root="https://test.com",
                client_id="client_id",
                client_secret="client_secret",
            )

            # Set valid token
            auth.generated_token = "valid_token"
            auth.expiry_time = datetime.datetime.now(
                datetime.timezone.utc
            ) + datetime.timedelta(minutes=50)

            request = requests.PreparedRequest()
            request.url = "https://test.com/api/v2/events"
            request.headers = {}

            auth(request)

            assert not mock_post.called
            assert request.headers["Authorization"] == "Bearer valid_token"
