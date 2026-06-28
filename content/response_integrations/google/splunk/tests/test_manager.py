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

import pathlib
import json
import unittest
from unittest.mock import patch, Mock

from splunk.core.SplunkManager import SplunkManager
from splunk.tests import const
from integration_testing.logger import Logger


# Constants
SEARCH_MODE = "Smart"
QUERY = "index='main'"
LIMIT = 1
SUCCESS_CODE = 200
FAILURE_CODE = 400
FROM_TIME = "-24h"
TO_TIME = "now"
SID = "1695292526.698688"
NOTABLE_EVENT_ID = ["0BA818C1-47B5-4120-BC1A-8"]
STATUS = 1
URGENCY = "high"
DISPOSITION = "5"
INDEX = "index"
EVENT = "host"

MOCK_DATA = json.loads(const.MOCK_DATA_FILE_NAME.read_text(encoding="utf-8"))

SPLUNK_EXECUTE_SEARCH_JOB_FOR_QUERY = MOCK_DATA.get(
    "splunk_execute_search_job_for_query"
)
SPLUNK_EXECUTE_IS_JOB_DONE = MOCK_DATA.get("splunk_query_execute_is_job_done")
SPLUNK_EXECUTE_GET_JOB_RESULTS = MOCK_DATA.get("splunk_execute_get_job_results")
SPLUNK_EXECUTE_DELETE_JOB = MOCK_DATA.get("splunk_query_execute_delete_job")
SEARCH_HOST_EVENT = MOCK_DATA.get("search_host_events")
EXPECTED_SEARCH_HOST_EVENT = json.dumps(MOCK_DATA.get("expected_host_event"))
SUBMIT_EVENT = MOCK_DATA.get("submit_events")
UPDATE_NOTABLE_EVENTS = MOCK_DATA.get("update_notable_events")
UPDATE_NOTABLE_EVENTS_EXCEPTION = MOCK_DATA.get("update_notable_events_exception")


class TestSplunk(unittest.TestCase):
    """Splunk Test Cases"""

    def setUp(self) -> None:
        """Initial configuration/setup before every test case run"""
        self.logger = Logger()
        data = const.CONFIG_PATH.read_text(encoding="utf-8")
        config = json.loads(data)
        user_name = config.get("Username")
        password = config.get("Password")
        server_address = config.get("Server Address")
        verify_ssl = bool(config.get("Verify SSL"))
        self.manager = SplunkManager(
            username=user_name,
            password=password,
            server_address=server_address,
            verify_ssl=verify_ssl,
            siemplify_logger=self.logger,
        )

    def test_connectivity_success(self) -> None:
        """Test for test connectivity method."""
        with patch("requests.Session.post", return_value=Mock()):
            self.assertEqual(
                self.manager.test_connectivity(),
                True,
                "Assertion error: mocking test connectivity failed.",
            )

    def test_connectivity_with_encoded_unicode_success(self) -> None:
        """Test for test connectivity method."""
        setattr(self.manager, "username", "$%#FYĐđצקЊกฃアィԱԳ😀🌍".encode())
        setattr(self.manager, "password", "$%#FYĐđצקЊกฃアィԱԳ😀🌍".encode())
        setattr(self.manager, "server_address", "https://example.com")
        self.manager.session.auth = (self.manager.username, self.manager.password)
        with self.assertRaises(Exception) as e:
            self.manager.test_connectivity()

        assert type(e.exception).__name__ == "SplunkHTTPException"

    def test_connectivity_with_decoded_unicode_failure(self) -> None:
        """Test for test connectivity method."""
        setattr(self.manager, "username", "$%#FYĐđצקЊกฃアィԱԳ😀🌍")
        setattr(self.manager, "password", "$%#FYĐđצקЊกฃアィԱԳ😀🌍")
        setattr(self.manager, "server_address", "https://unicode_error.com")
        self.manager.session.auth = (self.manager.username, self.manager.password)
        with self.assertRaises(Exception) as e:
            self.manager.test_connectivity()

        assert type(e.exception).__name__ == "SplunkHTTPException"
        assert str(e.exception) == "Unicode Error Occurred."

    def test_splunk_execute_query_search_job_for_query(self) -> None:
        """Test for search job for query"""
        setattr(self.manager, "server_address", "https://test_manager.com")
        result = self.manager.search_job_for_query(
            search_mode=SEARCH_MODE,
            query=QUERY,
            limit=LIMIT,
            from_time=FROM_TIME,
            to_time=TO_TIME,
            fields="",
        )
        self.assertEqual(result, SPLUNK_EXECUTE_SEARCH_JOB_FOR_QUERY["sid"])

    def test_splunk_execute_query_is_job_done(self) -> None:
        """Test for is job done"""
        setattr(self.manager, "server_address", "https://test_manager.com")
        result = self.manager.is_job_done(sid=SID)
        self.assertEqual(result, True)

    def test_splunk_execute_query_get_job_results(self) -> None:
        """Test for get job results"""
        setattr(self.manager, "server_address", "https://test_manager.com")
        result = self.manager.get_job_results(sid=SID, build_with="")
        self.assertGreater(len(result), 0)

    def test_splunk_execute_query_delete_job(self) -> None:
        """Test for delete job"""
        setattr(self.manager, "server_address", "https://test_manager.com")
        result = self.manager.delete_job(sid=SID)
        self.assertEqual(result, True)

    def test_update_notable_event(self) -> None:
        """Test for update notable events"""
        setattr(self.manager, "server_address", "https://test_manager.com")
        self.assertIsNone(
            self.manager.update_notable_event(
                notable_event_ids=NOTABLE_EVENT_ID,
                status=STATUS,
                urgency=URGENCY,
                new_owner="",
                comment="",
                disposition=DISPOSITION,
            )
        )

    def test_submit_event(self) -> None:
        """Test for submit events"""
        setattr(self.manager, "server_address", "https://test_manager.com")
        result = self.manager.submit_event(index=INDEX, event=EVENT)
        custom_result = vars(result)
        self.assertEqual(custom_result["raw_data"], SUBMIT_EVENT)

    @patch("requests.Session.get")
    def test_update_notable_event_raise_exception_failure(self, mock_get) -> None:
        """Test for UnableToUpdateNotableEvents exception"""

        mock_response = Mock()
        mock_response.status_code = FAILURE_CODE
        mock_get.return_value = mock_response

        with patch.object(self.manager, "validate_response", side_effect=Exception):
            with self.assertRaises(Exception):
                self.manager.update_notable_event(
                    notable_event_ids=NOTABLE_EVENT_ID,
                    status=STATUS,
                    urgency=URGENCY,
                    new_owner="",
                    comment="",
                    disposition=DISPOSITION,
                )

    def test_search_host_events(self) -> None:
        """Test for search host events"""
        result = self.manager.search_host_events(
            query=QUERY,
            limit=LIMIT,
            from_time=FROM_TIME,
            to_time=TO_TIME,
            fields="",
        )
        self.assertIsInstance(result, list)
