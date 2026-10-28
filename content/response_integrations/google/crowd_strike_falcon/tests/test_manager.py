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

"""Unit tests for CrowdStrikeFalcon Integration."""
import itertools
import json
import unittest
from collections.abc import Callable, Iterator
from copy import deepcopy
from typing import Any
from unittest.mock import MagicMock, Mock, call, patch
from uuid import uuid4

import requests
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager
from crowd_strike_falcon.core.exceptions import (
    CrowdStrikeBadRequestError,
    CrowdStrikeError,
    CrowdStrikeManagerError,
)

from crowd_strike_falcon.tests.test_constants import (
    ADD_COMMENT_TO_DETECTION_JSON,
    ADD_IDENTITY_PROTECTION_DETECTION_COMMENT_JSON,
    ADD_INCIDENT_COMMENT_INCIDENT_JSON,
    BAD_REQUEST_STATUS_CODE,
    BEHAVIOR_IDS,
    DETECTION_ID,
    GET_ALERT_DETAILS,
    GET_DEVICE_LOGIN_HISTORIES_JSON,
    GET_DEVICE_LOGIN_HISTORIES_OUT_JSON,
    GET_INCIDENT_BEHAVIORS_DETAILS_JSON,
    GET_INCIDENT_BEHAVIORS_JSON,
    GET_INCIDENT_DETAILS_JSON,
    GET_INCIDENTS_JSON,
    GET_STREAM_DETECTIONS_JSON,
    GET_UUID_SUCCESS_JSON,
    GET_VULNERABILITY_IDS_JSON,
    INCIDENT_ID,
    INCIDENT_ID_ASSIGN_TO,
    INCIDENT_ID_STATUS,
    INVALID_ID,
    INVALID_IDS,
    MOCK_DATA,
    REMIDIATION_DEAILS_JSON,
    SEARCH_DETECTION_JSON,
    SEARCH_DEVICES_IDS_LIST,
    SEARCH_INCIDENT_JSON,
    SUCCESS_STATUS_CODE,
    TEST_COMMENT,
    TEST_LIMIT_VALUE,
    TEST_SEVERITY_VALUE,
    TEST_UNIXTIMESTAMP,
    TEST_ZERO_VALUE,
    UPDATE_DETECTION_JSON,
    VULNERABILITY_DETAILS_JSON,
    GET_IOCs_JSON,
    IOC_IDs,
)


class TestCrowdStrikeManager(unittest.TestCase):
    """Unit tests for CrowdStrikeFalcon Integration."""

    def setUp(self) -> None:
        from pathlib import Path
        with open(Path(__file__).parent / "config.json", encoding="utf-8") as f:
            data = f.read()

        config = json.loads(data)

        api_root = config.get("Api Root")
        client_id = config.get("Client API ID")
        client_secret = config.get("Client API Secret")
        with patch.object(CrowdStrikeManager, "fetch_token") as mock_fetch_token:
            mock_fetch_token.return_value = ""
            self.manager = CrowdStrikeManager(
                api_root=api_root,
                client_id=client_id,
                client_secret=client_secret,
            )

    def test_test_connectivity(self) -> None:
        """Tests the connectivity to the API."""
        self.manager.test_connectivity = Mock(return_value=True)
        self.assertEqual(
            self.manager.test_connectivity(),
            True,
            "Assertion error: mocking test connectivity failed.",
        )

    def test_connectivity_failure(self) -> None:
        with patch.object(
            self.manager,
            "test_connectivity",
        ) as mock_test_connectivity:
            mock_test_connectivity.side_effect = CrowdStrikeError()
            with self.assertRaises(CrowdStrikeError):
                self.manager.test_connectivity()

    @patch.object(CrowdStrikeManager, "get_iocs")
    def test_get_iocs(self, mock_get_iocs: Mock) -> None:
        mock_get_iocs.return_value = GET_IOCs_JSON
        iocs = self.manager.get_iocs(
            ids=IOC_IDs, filter_logic="Equal", filter_value="md5",
        )
        self.assertEqual(iocs, GET_IOCs_JSON)

    @patch.object(CrowdStrikeManager, "search_devices_ids")
    def test_search_devices_ids(self, mock_search_devices_ids: Mock) -> None:
        params = {"starts_with_name": "CROWDSTRIKE-H03"}
        mock_search_devices_ids.return_value = SEARCH_DEVICES_IDS_LIST
        devices_ids = self.manager.search_devices_ids(**params)
        self.assertEqual(devices_ids, SEARCH_DEVICES_IDS_LIST)

    def test_search_devices_ids_with_valid_cid_success(self) -> None:
        expected_device_id = ["0bb7054c47484408a582422b90816e30"]
        mock_object = MagicMock()
        mock_object.json.return_value = MOCK_DATA.get("search_devices_ids_valid")
        mock_object.status_code = 200
        with patch.object(
            self.manager.session, "request", return_value=mock_object,
        ):
            params = {"hostname": "CROWDSTRIKE-H03", "cid": "mock_valid"}
            devices_ids = self.manager.search_devices_ids(**params)

        self.assertEqual(devices_ids, expected_device_id)

    @patch("crowd_strike_falcon.core.CrowdStrikeManager.PAGE_SIZE", 2)
    def test_search_devices_ids_with_multiple_pages(self) -> None:
        response_1 = {
            "meta": {
                "pagination": {
                    "offset": 0,
                    "limit": 2,
                    "total": 3
                }
            },
            "resources": [
                "id_1",
                "id_2"
            ],
            "errors": []
        }
        response_2 = {
            "meta": {
                "pagination": {
                    "offset": 2,
                    "limit": 2,
                    "total": 3
                }
            },
            "resources": [
                "id_3"
            ],
            "errors": []
        }

        mock_object_1 = MagicMock()
        mock_object_1.json.return_value = response_1
        mock_object_1.status_code = 200

        mock_object_2 = MagicMock()
        mock_object_2.json.return_value = response_2
        mock_object_2.status_code = 200

        with patch.object(
            self.manager.session, "request", side_effect=[mock_object_1, mock_object_2]
        ) as mock_request:
            params = {"hostname": "CROWDSTRIKE-H03", "cid": "mock_valid"}
            devices_ids = self.manager.search_devices_ids(**params)

        self.assertEqual(devices_ids, ["id_1", "id_2", "id_3"])
        self.assertEqual(mock_request.call_count, 2)

    @patch("crowd_strike_falcon.core.CrowdStrikeManager.PAGE_SIZE", 2)
    def test_search_devices_ids_empty_page_breaks_loop(self) -> None:
        response_1 = {
            "meta": {
                "pagination": {
                    "offset": 0,
                    "limit": 2,
                    "total": 3
                }
            },
            "resources": [
                "id_1",
                "id_2"
            ],
            "errors": []
        }
        response_2 = {
            "meta": {
                "pagination": {
                    "offset": 2,
                    "limit": 2,
                    "total": 3
                }
            },
            "resources": [],
            "errors": []
        }

        mock_object_1 = MagicMock()
        mock_object_1.json.return_value = response_1
        mock_object_1.status_code = 200

        mock_object_2 = MagicMock()
        mock_object_2.json.return_value = response_2
        mock_object_2.status_code = 200

        with patch.object(
            self.manager.session, "request", side_effect=[mock_object_1, mock_object_2]
        ) as mock_request:
            params = {"hostname": "CROWDSTRIKE-H03", "cid": "mock_valid"}
            devices_ids = self.manager.search_devices_ids(**params)

        self.assertEqual(devices_ids, ["id_1", "id_2"])
        self.assertEqual(mock_request.call_count, 2)

    def test_get_devices_chunking(self) -> None:
        ids = [f"id_{i}" for i in range(150)]

        response_1 = {
            "resources": [
                {"device_id": f"id_{i}"} for i in range(100)
            ],
            "errors": []
        }
        response_2 = {
            "resources": [
                {"device_id": f"id_{i}"} for i in range(100, 150)
            ],
            "errors": []
        }

        mock_object_1 = MagicMock()
        mock_object_1.json.return_value = response_1
        mock_object_1.status_code = 200

        mock_object_2 = MagicMock()
        mock_object_2.json.return_value = response_2
        mock_object_2.status_code = 200

        with patch.object(
            self.manager.session, "request", side_effect=[mock_object_1, mock_object_2]
        ) as mock_request:
            devices = self.manager.get_devices(devices_ids=ids)

        self.assertEqual(len(devices), 150)
        self.assertEqual(mock_request.call_count, 2)
        mock_request.assert_any_call(
            "GET",
            self.manager._get_full_url("entities_devices"),
            params={"ids": [f"id_{i}" for i in range(100)]}
        )
        mock_request.assert_any_call(
            "GET",
            self.manager._get_full_url("entities_devices"),
            params={"ids": [f"id_{i}" for i in range(100, 150)]}
        )


    def test_search_devices_ids_with_invalid_cid_failed(self) -> None:
        expected_err = (
            "Only your own CID can be provided for a non-falcon flight control CIDs "
            "for the 'cid' query field."
        )
        mock_object = MagicMock()
        mock_object.json.return_value = MOCK_DATA.get(
            "search_devices_ids_invalid",
        )
        mock_object.status_code = 400
        mock_error = requests.HTTPError("400 Client Error: Bad Request for url:")
        mock_error.response = mock_object
        mock_object.raise_for_status.side_effect = mock_error
        with patch.object(
            self.manager.session, "request", return_value=mock_object,
        ):
            params = {"hostname": "CROWDSTRIKE-H03", "cid": "mock_invalid"}
            with self.assertRaises(Exception) as err:
                self.manager.search_devices_ids(**params)

        self.assertEqual(
            type(err.exception).__name__,
            "CrowdStrikeBadRequestError",
        )
        assert expected_err in str(err.exception)

    @patch.object(CrowdStrikeManager, "get_vulnerability_ids")
    def test_get_vulnerability_ids(
        self, mock_get_vulnerability_ids: Mock,
    ) -> None:
        mock_get_vulnerability_ids.return_value = (
            GET_VULNERABILITY_IDS_JSON, 117)
        vulnerability_ids = self.manager.get_vulnerability_ids(
            aid=SEARCH_DEVICES_IDS_LIST[0], limit=2,
        )
        self.assertEqual(vulnerability_ids, (GET_VULNERABILITY_IDS_JSON, 117))

    @patch.object(
        CrowdStrikeManager, "get_vulnerabilities_detailed_information",
    )
    def test_get_vulnerabilities_detailed_information(
        self, mock_get_vulnerabilities: Mock,
    ) -> None:
        mock_get_vulnerabilities.return_value = VULNERABILITY_DETAILS_JSON
        vulnerability_details = (
            self.manager.get_vulnerabilities_detailed_information(
                "d498fc988cd34ab3b9",
            )
        )
        self.assertEqual(vulnerability_details, VULNERABILITY_DETAILS_JSON)

    @patch.object(CrowdStrikeManager, "get_remediation_details")
    def test_get_remediation_details(
        self, mock_get_remediation_details: Mock,
    ) -> None:
        mock_get_remediation_details.return_value = REMIDIATION_DEAILS_JSON
        remediation_detail = self.manager.get_remediation_details(
            ids={"951a5d56893a34c7a7f50a883551cde7"},
        )
        self.assertEqual(remediation_detail, REMIDIATION_DEAILS_JSON)

    @patch.object(CrowdStrikeManager, "get_stream_detections")
    def test_get_stream_detections(
        self, mock_get_stream_detections: Mock,
    ) -> None:
        def stream_detections_generator():
            yield GET_STREAM_DETECTIONS_JSON

        mock_get_stream_detections.return_value = stream_detections_generator
        stream_detections = self.manager.get_stream_detections(
            app_name="siemplify2158fa98a22f4c9babe61",
            offset=None,
            limit=5,
        )
        self.assertEqual(stream_detections, stream_detections_generator)

    @patch.object(CrowdStrikeManager, "get_alerts_details")
    def test_get_alert_details(self, mock_get_alerts_details: Mock) -> None:
        detection_id = "27fe4e476ca3490b8476b2b6650e5a74"

        mock_get_alerts_details.return_value = GET_ALERT_DETAILS
        alert_details = self.manager.get_alerts_details(ids=detection_id)
        self.assertEqual(alert_details, GET_ALERT_DETAILS)

    def test_update_alert_success(self) -> None:
        mock_object = MagicMock()
        mock_object.json.return_value = {}
        mock_object.status_code = 200

        alert_id = "abcd"
        status = "Closed"
        verdict = "True Positive"
        assign_to = "xyz"

        with patch.object(
            self.manager.session, "request", return_value=mock_object,
        ):
            self.manager.update_alert(alert_id, status, verdict, assign_to)

    def test_update_alert_with_invalid_alert_id_failed(self) -> None:
        mock_object = MagicMock()
        mock_object.status_code = 400
        mock_error = requests.HTTPError("400 Client Error: Bad Request for url:")
        mock_error.response = mock_object
        mock_object.raise_for_status.side_effect = mock_error

        with patch.object(
            self.manager.session, "request", return_value=mock_object,
        ):
            alert_id = "abcd"
            assign_to = "xyz"
            with self.assertRaises(Exception) as err:
                self.manager.update_alert(alert_id=alert_id, assign_to=assign_to)
        self.assertEqual(
            type(err.exception).__name__,
            "CrowdStrikeBadRequestError",
        )

    def test_add_comment_to_alert_success(self) -> None:
        mock_object = MagicMock()
        mock_object.json.return_value = {}
        mock_object.status_code = 200

        alert_id = "abcd"
        comment = "commit"

        with patch.object(
            self.manager.session, "request", return_value=mock_object,
        ):
            self.manager.add_comment_to_alert(alert_id, comment)

    def test_add_comment_to_alert_with_invalid_alert_id_failed(self) -> None:
        mock_object = MagicMock()
        mock_object.status_code = 400
        mock_error = requests.HTTPError("400 Client Error: Bad Request for url:")
        mock_error.response = mock_object
        mock_object.raise_for_status.side_effect = mock_error

        with patch.object(
            self.manager.session, "request", return_value=mock_object,
        ):
            alert_id = "abcd"
            comment = "xyz"
            with self.assertRaises(Exception) as err:
                self.manager.add_comment_to_alert(alert_id, comment)

        self.assertEqual(
            type(err.exception).__name__,
            "CrowdStrikeBadRequestError",
        )

    @patch.object(CrowdStrikeManager, "update_detection")
    def test_update_detection(self, mock_update_detection: Mock) -> None:
        mock_update_detection.return_value = UPDATE_DETECTION_JSON
        response = self.manager.update_detection(
            uuid=uuid4(),
            detection_ids=[UPDATE_DETECTION_JSON["incident_id"]],
            detection_status=30,
        )
        self.assertEqual(response, UPDATE_DETECTION_JSON)

    @patch.object(CrowdStrikeManager, "add_comment_to_detection")
    def test_add_comment_to_detection_invalid_detection_id(
        self, mock_add_comment_to_detection: Mock,
    ) -> None:
        invalid_detection_id = "invalid_id"
        err_msg = (
            "Unable to get status of the detection with"
            f" identifier {invalid_detection_id}"
        )
        mock_add_comment_to_detection.side_effect = CrowdStrikeManagerError(
            err_msg,
        )
        with self.assertRaises(CrowdStrikeManagerError):
            self.manager.add_comment_to_detection(
                comment="test comment",
                detection_ids=invalid_detection_id,
                status="normal",
            )

    @patch.object(CrowdStrikeManager, "add_comment_to_detection")
    def test_add_comment_to_detection(self, mock_validate_response: Mock) -> None:
        mock_validate_response.return_value = ADD_COMMENT_TO_DETECTION_JSON
        self.assertEqual(
            self.manager.add_comment_to_detection(
                comment="test comment",
                detection_ids=ADD_COMMENT_TO_DETECTION_JSON["incident_id"],
                status="normal",
            ),
            ADD_COMMENT_TO_DETECTION_JSON,
        )

    def test_get_device_login_histories(self) -> None:
        device_login_histories_mock = Mock()
        device_login_histories_mock.status_code = SUCCESS_STATUS_CODE
        device_login_histories_mock.json.return_value = (
            GET_DEVICE_LOGIN_HISTORIES_JSON)

        with patch.object(
            self.manager.session,
            "post",
            return_value=device_login_histories_mock,
        ):
            devices_login_histories = self.manager.get_devices_login_histories(
                ids=["d498fc988cd34ab3b946b46cff08d88a"],
            )
            devices_login_histories = [
                vars(history) for history in devices_login_histories
            ]
        self.assertEqual(
            [devices_login_histories], GET_DEVICE_LOGIN_HISTORIES_OUT_JSON,
        )

    def test_search_detection_success(self) -> None:
        """Tests the happy path for the search_detection() method."""
        search_detection_mock = Mock()
        search_detection_mock.status_code = SUCCESS_STATUS_CODE
        search_detection_mock.json.return_value = (
            ADD_IDENTITY_PROTECTION_DETECTION_COMMENT_JSON
        )

        with patch.object(
            self.manager.session, "post", return_value=search_detection_mock,
        ):
            result = self.manager.search_detection(id_=DETECTION_ID)

        self.assertIsNone(result, "Failed to search detection")

    def test_search_detection_invalid_id_failure(self) -> None:
        """Tests the failure path for the search_detection() method."""
        search_detection_mock = Mock()
        search_detection_mock.status_code = BAD_REQUEST_STATUS_CODE

        with patch.object(
            self.manager.session, "post",
            return_value=search_detection_mock,
        ) as test:
            test.side_effect = CrowdStrikeBadRequestError("An error occurred")
            with self.assertRaises(CrowdStrikeBadRequestError):
                self.manager.search_detection(id_=INVALID_ID)

    def test_update_alert_detail_success(self) -> None:
        """Tests the happy path for the update_alert_detail() method."""
        search_detection_mock = Mock()
        search_detection_mock.status_code = SUCCESS_STATUS_CODE
        search_detection_mock.json.return_value = SEARCH_DETECTION_JSON

        update_alert_detail_mock = Mock()
        update_alert_detail_mock.status_code = SUCCESS_STATUS_CODE
        update_alert_detail_mock.json.return_value = (
            ADD_IDENTITY_PROTECTION_DETECTION_COMMENT_JSON
        )

        with patch.object(
            self.manager.session,
            "patch",
            return_value=update_alert_detail_mock,
        ), patch.object(
            self.manager.session,
            "post",
            return_value=search_detection_mock,
        ):
            result = self.manager.update_alert_detail(
                comment=TEST_COMMENT, detection_id=DETECTION_ID,
            )

        self.assertIsNone(result, "Failed to update the detection id")

    def test_search_incident_success(self) -> None:
        """Tests the happy path for the search_incident() method."""
        search_incident_mock = Mock()
        search_incident_mock.status_code = SUCCESS_STATUS_CODE
        search_incident_mock.json.return_value = SEARCH_INCIDENT_JSON

        with patch.object(
            self.manager.session, "post", return_value=search_incident_mock,
        ):
            result = self.manager.search_incident(incident_id=INCIDENT_ID)

        self.assertEqual(
            result.incident_id,
            SEARCH_INCIDENT_JSON.get("resources")[0].get("incident_id"),
        )
        self.assertEqual(
            int(result.incident_type),
            SEARCH_INCIDENT_JSON.get("resources")[0].get("incident_type"),
        )

    def test_search_incident_invalid_id_failure(self) -> None:
        """Tests the failure path for the search_incident() method."""
        search_incident_mock = Mock()
        search_incident_mock.status_code = BAD_REQUEST_STATUS_CODE

        with patch.object(
            self.manager.session, "post",
            return_value=search_incident_mock,
        ) as test:
            test.side_effect = CrowdStrikeBadRequestError("An error occurred")
            with self.assertRaises(CrowdStrikeBadRequestError):
                self.manager.search_incident(incident_id=INVALID_ID)

    def test_add_incident_comment_success(self) -> None:
        """Tests the happy path for the add_incident_comment() method."""
        search_incident_mock = Mock()
        search_incident_mock.status_code = SUCCESS_STATUS_CODE
        search_incident_mock.json.return_value = SEARCH_INCIDENT_JSON

        add_incident_comment_mock = Mock()
        add_incident_comment_mock.status_code = SUCCESS_STATUS_CODE
        add_incident_comment_mock.json.return_value = (
            ADD_INCIDENT_COMMENT_INCIDENT_JSON)

        with patch.object(
            self.manager.session,
            "post",
            return_value=add_incident_comment_mock,
        ), patch.object(
            self.manager.session,
            "post",
            return_value=search_incident_mock,
        ):
            result = self.manager.add_incident_comment(
                comment=TEST_COMMENT, incident_id=INCIDENT_ID,
            )

        self.assertIsNone(result, "Failed to add comment to incident id")

    def test_update_incident_success(self) -> None:
        """Tests the happy path for the update_incident() method."""
        search_incident_mock = Mock()
        search_incident_mock.status_code = SUCCESS_STATUS_CODE
        search_incident_mock.json.return_value = SEARCH_INCIDENT_JSON

        update_incident_mock = Mock()
        update_incident_mock.status_code = SUCCESS_STATUS_CODE

        get_uuid_mock = Mock()
        get_uuid_mock.status_code = SUCCESS_STATUS_CODE
        get_uuid_mock.json.return_value = GET_UUID_SUCCESS_JSON

        with patch.object(
            self.manager.session, "post", return_value=update_incident_mock,
        ), patch.object(
            self.manager.session, "post", return_value=search_incident_mock,
        ), patch.object(
            self.manager.session, "get", return_value=get_uuid_mock,
        ):
            result = self.manager.update_incident(
                incident_id=INCIDENT_ID,
                id_status=INCIDENT_ID_STATUS,
                assign_to=INCIDENT_ID_ASSIGN_TO,
            )

        self.assertIsNone(result, "Failed to update an incident")

    def test_get_incidents_success(self) -> None:
        """Tests the happy path for the get_incidents() method."""
        get_incidents_mock = Mock()
        get_incidents_mock.status_code = SUCCESS_STATUS_CODE
        get_incidents_mock.json.return_value = GET_INCIDENTS_JSON

        get_incident_details_mock = Mock()
        get_incident_details_mock.status_code = SUCCESS_STATUS_CODE
        get_incident_details_mock.json.return_value = GET_INCIDENT_DETAILS_JSON

        with patch.object(
            self.manager.session, "request", return_value=get_incidents_mock,
        ), patch.object(
            self.manager.session, "post",
            return_value=get_incident_details_mock,
        ):
            result = self.manager.get_incidents(
                severity=TEST_SEVERITY_VALUE,
                last_success_datetime=TEST_UNIXTIMESTAMP,
                limit=TEST_LIMIT_VALUE,
            )

        self.assertGreater(len(result), TEST_ZERO_VALUE)
        self.assertEqual(
            result[0].incident_id,
            GET_INCIDENT_DETAILS_JSON.get("resources")[0].get("incident_id"),
        )
        self.assertEqual(
            int(result[0].incident_type),
            GET_INCIDENT_DETAILS_JSON.get("resources")[0].get("incident_type"),
        )

    def test_get_incident_behaviors_success(self) -> None:
        """Tests the happy path for the get_incident_behaviors() method."""
        get_incidents_behavior_mock = Mock()
        get_incidents_behavior_mock.status_code = SUCCESS_STATUS_CODE
        get_incidents_behavior_mock.json.return_value = (
            GET_INCIDENT_BEHAVIORS_JSON)

        with patch.object(
            self.manager.session,
            "get",
            return_value=get_incidents_behavior_mock,
        ):
            result = self.manager.get_incident_behaviors(incident_id=INCIDENT_ID)

        self.assertGreater(len(result), TEST_ZERO_VALUE)

    def test_get_incident_behaviors_details_success(self) -> None:
        """Tests the happy path for the get_incident_behaviors_details() method."""
        get_incident_behaviors_details_mock = Mock()
        get_incident_behaviors_details_mock.status_code = SUCCESS_STATUS_CODE
        get_incident_behaviors_details_mock.json.return_value = (
            GET_INCIDENT_BEHAVIORS_DETAILS_JSON
        )

        with patch.object(
            self.manager.session,
            "post",
            return_value=get_incident_behaviors_details_mock,
        ):
            result = self.manager.get_incident_behaviors_details(ids=BEHAVIOR_IDS)

        self.assertGreater(len(result), TEST_ZERO_VALUE)
        self.assertEqual(
            result[0].raw_data,
            GET_INCIDENT_BEHAVIORS_DETAILS_JSON.get("resources")[0],
        )

    def test_get_incident_behaviors_invalid_id_failure(self) -> None:
        """Tests the failure path for get_incident_behaviors() method."""
        get_incident_behaviors_details_mock = Mock()
        get_incident_behaviors_details_mock.status_code = BAD_REQUEST_STATUS_CODE

        with patch.object(
            self.manager.session,
            "post",
            return_value=get_incident_behaviors_details_mock,
        ) as test:
            test.side_effect = CrowdStrikeBadRequestError(
                "An error occurred",
            )
            with self.assertRaises(CrowdStrikeBadRequestError):
                self.manager.get_incident_behaviors_details(ids=INVALID_IDS)

    def test_execute_responder_script_valid_success(self) -> None:
        expected_cloud_request_id = "c4298c8e-121b-4267-8051-c22b2590014b"
        mock_device_id = "mock_device_id"
        mock_session_id = "mock_session_id"
        command = "echo 'hello world'"
        mock_object = MagicMock()
        mock_object.json.return_value = MOCK_DATA.get(
            "execute_responder_script_valid",
        )
        mock_object.status_code = 201
        with patch.object(
            self.manager.session, "post", return_value=mock_object,
        ):
            result = self.manager.execute_responder_script(
                device_id=mock_device_id,
                session_id=mock_session_id,
                command=command,
            )

        self.assertEqual(result, expected_cloud_request_id)

    def test_execute_responder_script_valid_with_none_success(self) -> None:
        mock_device_id = "mock_device_id"
        mock_session_id = "mock_session_id"
        command = "echo 'hello world'"
        mock_object = MagicMock()
        mock_object.json.return_value = MOCK_DATA.get(
            "execute_responder_script_valid_failure",
        )
        mock_object.status_code = 201
        with patch.object(
            self.manager.session, "post", return_value=mock_object,
        ):
            result = self.manager.execute_responder_script(
                device_id=mock_device_id,
                session_id=mock_session_id,
                command=command,
            )

        self.assertEqual(result, None)

    def test_execute_responder_script_invalid_failed(self) -> None:
        expected_err = "Command is not valid"
        mock_device_id = "mock_device_id"
        mock_session_id = "mock_session_id"
        command = "echo 'hello world'"
        mock_object = MagicMock()
        mock_object.json.return_value = MOCK_DATA.get(
            "execute_responder_script_invalid",
        )
        mock_object.status_code = 400
        mock_error = requests.HTTPError("400 Client Error: Bad Request for url:")
        mock_error.response = mock_object
        mock_object.raise_for_status.side_effect = mock_error
        with patch.object(
            self.manager.session, "request", return_value=mock_object,
        ), self.assertRaises(Exception) as err:
            self.manager.execute_responder_script(
                device_id=mock_device_id,
                session_id=mock_session_id,
                command=command,
            )

        self.assertEqual(
            type(err.exception).__name__,
            "CrowdStrikeSessionCreatedError",
        )
        assert expected_err in str(err.exception)

    def test_fetch_token_without_customer_id(self) -> None:
        """Verify 'member_cid' is not in payload if customer_id is not provided."""
        from pathlib import Path
        with open(Path(__file__).parent / "config.json", encoding="utf-8") as f:
            config = json.load(f)

        with patch(
            "crowd_strike_falcon.tests.core.session.CrowdStrikeFalconSession.post",
        ) as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"access_token": "parent_token"}
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            CrowdStrikeManager(
                client_id=config.get("Client API ID"),
                client_secret=config.get("Client API Secret"),
                api_root=config.get("API Root"),
            )

            mock_post.assert_called_once()
            _, call_kwargs = mock_post.call_args
            payload = call_kwargs.get("data")

            self.assertNotIn("member_cid", payload)
            self.assertEqual(payload["client_id"], config.get("Client API ID"))

    def test_fetch_token_with_customer_id(self) -> None:
        """Verify 'member_cid' is added to payload when customer_id is provided."""
        from pathlib import Path
        with open(Path(__file__).parent / "config.json", encoding="utf-8") as f:
            config = json.load(f)

        with patch(
            "crowd_strike_falcon.tests.core.session.CrowdStrikeFalconSession.post",
        ) as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"access_token": "child_token"}
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            CrowdStrikeManager(
                client_id=config.get("Client API ID"),
                client_secret=config.get("Client API Secret"),
                api_root=config.get("API Root"),
                customer_id="child_tenant_12345",
            )

            mock_post.assert_called_once()
            _, call_kwargs = mock_post.call_args
            payload = call_kwargs.get("data")

            self.assertIn("member_cid", payload)
            self.assertEqual(payload["member_cid"], "child_tenant_12345")
            self.assertEqual(payload["client_id"], config.get("Client API ID"))

    def test_get_stream_detections_passes_correct_timeout(self) -> None:
        """Verify that the streaming request includes the correct timeout."""
        mock_stream_obj = MagicMock()
        mock_stream_obj.url = "https://fake.stream.url/stream"
        mock_stream_obj.token = "fake_token"

        mock_response = MagicMock()
        mock_response.iter_lines.return_value = []
        mock_response.status_code = 200

        with patch.object(
            self.manager, "_discover_streams", return_value=mock_stream_obj,
        ) as mock_discover, patch.object(
            self.manager.session, "get", return_value=mock_response,
        ) as mock_session_get:
            list(
                self.manager.get_stream_detections(
                    app_name="test_app", offset=0,
                ),
            )

            mock_discover.assert_called_once()
            mock_session_get.assert_called_once()
            _, call_kwargs = mock_session_get.call_args
            self.assertEqual(call_kwargs.get("timeout"), (5, 300))

    def test_get_stream_detections_handles_read_timeout(self) -> None:
        """Verify ReadTimeout is re-raised as a CrowdStrikeManagerError."""
        mock_stream_obj = MagicMock()
        mock_stream_obj.url = "https://fake.stream.url/stream"
        mock_stream_obj.token = "fake_token"

        with patch.object(
            self.manager, "_discover_streams", return_value=mock_stream_obj,
        ), patch.object(
            self.manager.session,
            "get",
            side_effect=requests.exceptions.ReadTimeout(
                "Simulated Read Timed out for test",
            ),
        ):
            with self.assertRaises(Exception) as cm:
                list(
                    self.manager.get_stream_detections(
                        app_name="test_app", offset=0,
                    ),
                )
            self.assertEqual(
                type(cm.exception).__name__, "CrowdStrikeManagerError",
            )
            self.assertIn(
                "Stream to fetch detections reaches timeout",
                str(cm.exception),
            )

    @staticmethod
    def _get_offset_paginated_requests(
        resources: list, total_items: int, pagination_step: int,
    ) -> list:
        """Creates a list of responses for paginated requests.

        Args:
            resources: A list of resources to be paginated.
            total_items: The total number of items in the paginated response.
            pagination_step: The number of items per page.

        Returns:
            A list of responses.
            Example of the data returned by `mock_response.json()`:
                {
                    "resources": ["item-1", "item-2"],
                    "meta": {"pagination": {"total": 2}},
                }

        """
        return [
            {
                "resources": resources[i : i + pagination_step],
                "meta": {"pagination": {"total": total_items}},
            }
            for i in range(0, len(resources), pagination_step)
        ]

    @staticmethod
    def _paginated_requests_as_side_effects(responses):
        mocked_responses = []
        for response in responses:
            mock_response = Mock()
            mock_response.json.return_value = response
            mocked_responses.append(mock_response)
        return mocked_responses

    @staticmethod
    def intercepting_side_effect_calls(
        captured_calls: list,
        response_iterator: Iterator[Any],
    ) -> Callable:
        """Creates a mock side_effect wrapper to test code with mutable args.

        This factory solves the common `unittest.mock` problem where
        `mock.call_args_list` stores *references* to arguments. If the
        code-under-test mutates a dictionary (e.g., `params["offset"] += 1`
        in a loop), all recorded calls will incorrectly show the *final*
        state of that dictionary, causing assertions to fail.

        This wrapper intercepts each call to:
        1. Capture a `deepcopy` of the `*args` and `**kwargs` at that moment.
        2. Append this immutable snapshot as a `mock.call` object to the
            provided `captured_calls` list.
        3. Return the next item from the `response_iterator`.

        Args:
            captured_calls: An empty list (passed by ref) that will
                be populated with the `mock.call` snapshots.
            response_iterator: An iterator (e.g., `iter(mock_responses)`)
                that yields the desired mock responses in order.

        Returns:
            A callable wrapper function to be assigned to `mock.side_effect`.

        """
        def wrapper(*args, **kwargs):
            captured_calls.append(call(*deepcopy(args), **deepcopy(kwargs)))
            return next(response_iterator)

        return wrapper

    def test_pagination_generator_last_page_is_not_complete(self):
        """Tests the pagination generator when the last page is not complete."""
        test_url = "test/endpoint"
        page_size = 2

        # Create a list of 5 resources to paginate through.
        resources = [f"item-{i}" for i in range(1, 6)]
        paginated_requests = self._get_offset_paginated_requests(
            resources, len(resources), page_size,
        )
        side_effects = self._paginated_requests_as_side_effects(paginated_requests)

        captured_calls = []
        response_iterator = iter(side_effects)

        side_effect = self.intercepting_side_effect_calls(
            captured_calls, response_iterator,
        )

        with patch.object(
            self.manager.session,
            "request",
            side_effect=side_effect,
        ) as mock_request:
            pages_generator = self.manager.offset_pagination_generator(
                url=test_url,
                page_size=page_size,
            )
            result_pages = list(pages_generator)

        # Verify that the generator yielded all 5 items.
        assert len(result_pages) == 5, "Should yield 5 items."
        # Verify that the request was called 3 times (2 full pages + 1 partial page).
        assert mock_request.call_count == 3, "Should have called 3 times."

        expected_calls = [
            call(
                "GET",
                test_url,
                params={"offset": 0, "limit": page_size},
                json=None,
            ),
            call(
                "GET",
                test_url,
                params={"offset": 2, "limit": page_size},
                json=None,
            ),
            call(
                "GET",
                test_url,
                params={"offset": 4, "limit": page_size},
                json=None,
            ),
        ]
        assert captured_calls == expected_calls

    def test_pagination_generator_last_page_is_complete(self):
        """Tests the pagination generator when the last page is complete."""
        test_url = "test/endpoint"
        page_size = 2

        # Create a list of 4 resources to paginate through.
        resources = [f"item-{i}" for i in range(1, 5)]
        paginated_requests = self._get_offset_paginated_requests(
            resources, len(resources), page_size,
        )
        side_effects = self._paginated_requests_as_side_effects(paginated_requests)

        captured_calls = []
        response_iterator = iter(side_effects)

        side_effect = self.intercepting_side_effect_calls(
            captured_calls, response_iterator,
        )

        with patch.object(
            self.manager.session,
            "request",
            side_effect=side_effect,
        ) as mock_request:
            pages_generator = self.manager.offset_pagination_generator(
                url=test_url,
                page_size=page_size,
            )
            result_pages = list(pages_generator)

        # Verify that the generator yielded all 4 items.
        assert len(result_pages) == 4, "Should yield 4 items."
        # Verify that the request was called 2 times (2 full pages).
        assert mock_request.call_count == 2, "Should have been called 2 times."

        expected_calls = [
            call(
                "GET",
                test_url,
                params={"offset": 0, "limit": page_size},
                json=None,
            ),
            call(
                "GET",
                test_url,
                params={"offset": 2, "limit": page_size},
                json=None,
            ),
        ]
        assert captured_calls == expected_calls

    def test_pagination_generator_page_has_less_data_then_requested(self):
        """Tests the pagination generator when a page has less data than requested."""
        test_url = "test/endpoint"
        page_size_param = 3

        # Create a list of 2 resources, which is less than the page size.
        page_1_resources = ["item-1", "item-2"]

        total_items = len(page_1_resources)

        page_1_response = {
            "resources": page_1_resources,
            "meta": {"pagination": {"total": total_items}},
        }

        mock_response_1 = Mock()
        mock_response_1.json.return_value = page_1_response

        captured_calls = []
        response_iterator = iter([mock_response_1])

        side_effect = self.intercepting_side_effect_calls(
            captured_calls, response_iterator,
        )

        with patch.object(
            self.manager.session,
            "request",
            side_effect=side_effect,
        ) as mock_request:
            pages_generator = self.manager.offset_pagination_generator(
                url=test_url,
                page_size=page_size_param,
            )
            result_pages = list(pages_generator)

        # Verify that the generator yielded all 2 items.
        assert len(result_pages) == 2, "Should yield 2 items."

        # Verify that the request was called only once.
        assert mock_request.call_count == 1, "Should have been called 1 time."
        expected_calls = [
            call(
                "GET",
                test_url,
                params={"offset": 0, "limit": page_size_param},
                json=None,
            ),
        ]
        assert captured_calls == expected_calls

    def test_get_device_by_host_name_no_device_ids(self):
        """Tests getting a device by hostname when no device IDs are found."""
        get_device_ids_url = "devices/queries/devices/v1"

        # Mock the response for getting device IDs to return an empty list.
        device_ids_response = {
            "resources": [],
            "meta": {"pagination": {"total": 0}},
        }

        device_ids_mock_response = Mock()
        device_ids_mock_response.json.return_value = device_ids_response

        captured_calls = []
        response_iterator = iter([device_ids_mock_response])

        side_effect = self.intercepting_side_effect_calls(
            captured_calls, response_iterator,
        )

        with patch.object(
            self.manager.session,
            "request",
            side_effect=side_effect,
        ) as mock_request:
            devices = self.manager.get_devices_by_hostname(
                hostname="crowdstrike",
                filter_strategy="Contains",
                cid="cid",
            )

        # Verify that no devices are returned.
        assert len(devices) == 0, "Should return 0 items."

        # Verify that the request to get device IDs was made once.
        assert mock_request.call_count == 1, "Should have been called 1 time."
        expected_calls = [
            call(
                "GET",
                get_device_ids_url,
                params={"filter": "cid: 'cid'", "offset": 0, "limit": 5000},
                json=None,
            ),
        ]
        assert captured_calls == expected_calls

    def test_get_device_by_host_name_filter_contains(self):
        """Tests getting a device by hostname with the 'Contains' filter."""
        get_device_ids_url = "devices/queries/devices/v1"
        page_size = 2

        # Mock the responses for getting device IDs.
        device_ids_resources = [f"device-{i}" for i in range(1, 7)]
        device_ids_paginated_requests = self._get_offset_paginated_requests(
            device_ids_resources, len(device_ids_resources), page_size,
        )
        device_ids_side_effects = self._paginated_requests_as_side_effects(
            device_ids_paginated_requests,
        )

        get_device_details_url = "devices/entities/devices/v2"

        # Mock the responses for getting device details.
        device_details_resources = [
            {"device_id": f"device-{i}", "hostname": "noname", "cid": "cid"}
            for i in range(1, 7)
        ]
        # The hostname to search. We expect to go through all data to find it.
        device_details_resources[-1]["hostname"] = "crowdstrike"

        device_details_requests = self._get_offset_paginated_requests(
            device_details_resources, page_size, page_size,
        )
        device_details_side_effects = self._paginated_requests_as_side_effects(
            device_details_requests,
        )

        # Combine the side effects for device IDs and device details.
        combined_side_effects = itertools.chain.from_iterable(
            zip(device_ids_side_effects, device_details_side_effects),
        )

        captured_calls = []

        side_effect = self.intercepting_side_effect_calls(
            captured_calls, combined_side_effects,
        )

        with patch.object(
            self.manager.session,
            "request",
            side_effect=side_effect,
        ) as mock_request:
            devices = self.manager.get_devices_by_hostname(
                hostname="crowdstrike",
                filter_strategy="Contains",
                cid="cid",
                page_size=page_size,
            )

        # Verify that one device is returned.
        assert len(devices) == 1, "Should have returned 1 item."

        # Verify that the requests were made as expected.
        assert mock_request.call_count == 6, "Should have been called 6 times."
        expected_calls = [
            # ==== Pipeline Iteration 1 ====
            call(
                "GET",
                get_device_ids_url,
                params={"filter": "cid: 'cid'", "offset": 0, "limit": 2},
                json=None,
            ),
            call(
                "POST",
                get_device_details_url,
                params={},
                json={"ids": device_ids_resources[0:2]},
            ),
            # ==== Pipeline Iteration 2 ====
            call(
                "GET",
                get_device_ids_url,
                params={"filter": "cid: 'cid'", "offset": 2, "limit": 2},
                json=None,
            ),
            call(
                "POST",
                get_device_details_url,
                params={},
                json={"ids": device_ids_resources[2:4]},
            ),
            # ==== Pipeline Iteration 3 ====
            call(
                "GET",
                get_device_ids_url,
                params={"filter": "cid: 'cid'", "offset": 4, "limit": 2},
                json=None,
            ),
            call(
                "POST",
                get_device_details_url,
                params={},
                json={"ids": device_ids_resources[4:6]},
            ),
        ]
        assert captured_calls == expected_calls

    def test_get_device_by_host_name_filter_equal_no_unnecessary_calls(self):
        """Tests that no unnecessary API calls are made when using the 'Equal' filter.
        """
        page_size = 2
        limit = 1

        get_device_ids_url = "devices/queries/devices/v1"

        # Mock the responses for getting device IDs.
        device_ids_resources = [f"device-{i}" for i in range(1, 7)]
        device_ids_paginated_requests = self._get_offset_paginated_requests(
            device_ids_resources, len(device_ids_resources), page_size,
        )
        device_ids_side_effects = self._paginated_requests_as_side_effects(
            device_ids_paginated_requests,
        )

        get_device_details_url = "devices/entities/devices/v2"

        # Mock the responses for getting device details.
        device_details_resources = [
            {"device_id": f"device-{i}", "hostname": "crowdstrike", "cid": "cid"}
            for i in range(1, 7)
        ]
        device_details_requests = self._get_offset_paginated_requests(
            device_details_resources, page_size, page_size,
        )
        device_details_side_effects = self._paginated_requests_as_side_effects(
            device_details_requests,
        )

        # Combine the side effects for device IDs and device details.
        combined_side_effects = itertools.chain.from_iterable(
            zip(device_ids_side_effects, device_details_side_effects),
        )

        captured_calls = []

        side_effect = self.intercepting_side_effect_calls(
            captured_calls, combined_side_effects,
        )

        with patch.object(
            self.manager.session,
            "request",
            side_effect=side_effect,
        ) as mock_request:
            devices = self.manager.get_devices_by_hostname(
                hostname="crowdstrike",
                filter_strategy="Equal",
                cid="cid",
                limit=limit,
                page_size=page_size,
            )

        # Verify that one device is returned.
        assert len(devices) == 1, "Should have returned 1 items."

        # Verify that only two API calls were made.
        assert mock_request.call_count == 2, "Should have 2 expected calls."
        mock_request.assert_has_calls(
            [
                # ==== Pipeline Iteration 1 ====
                call(
                    "GET",
                    get_device_ids_url,
                    params={
                        "filter": "hostname: ['crowdstrike']+cid: 'cid'",
                        "offset": 0,
                        "limit": limit,
                    },
                    json=None,
                ),
                call(
                    "POST",
                    get_device_details_url,
                    params={},
                    json={"ids": device_ids_resources[0:limit]},
                ),
            ],
        )

    def test_get_uploaded_iocs_no_ioc_ids(self):
        """Tests getting uploaded iocs when no ioc IDs are found."""
        get_ioc_ids_url = "iocs/queries/indicators/v1"

        # Mock the response for getting ioc IDs to return an empty list.
        ioc_ids_response = {
            "resources": [],
            "meta": {"pagination": {"total": 0, "after": "token"}},
        }

        ioc_ids_mock_response = Mock()
        ioc_ids_mock_response.json.return_value = ioc_ids_response

        captured_calls = []
        response_iterator = iter([ioc_ids_mock_response])

        side_effect = self.intercepting_side_effect_calls(
            captured_calls, response_iterator,
        )

        with patch.object(
            self.manager.session,
            "request",
            side_effect=side_effect,
        ) as mock_request:
            iocs = self.manager.get_uploaded_iocs(
                ioc_types=["md5"],
                ioc_value="hash_value",
                filter_strategy="Equal",
            )

        # Verify that no iocs are returned.
        assert len(iocs) == 0, "Should return 0 items."

        # Verify that the request to get ioc IDs was made once.
        assert mock_request.call_count == 1, "Should have been called 1 time."
        expected_calls = [
            call(
                "GET",
                get_ioc_ids_url,
                params={"filter": "type:['md5']+value:'hash_value'", "limit": 500},
                json=None,
            ),
        ]
        assert captured_calls == expected_calls

    def test_get_uploaded_iocs_filter_contains(self):
        """Tests getting uploaded iocs with the 'Contains' filter."""
        get_ioc_ids_url = "iocs/queries/indicators/v1"
        page_size = 2

        # Mock the responses for getting ioc IDs.
        ioc_ids_resources = [f"ioc-{i}" for i in range(1, 7)]
        ioc_ids_paginated_requests = self._get_token_paginated_requests(
            ioc_ids_resources, len(ioc_ids_resources), page_size,
        )
        ioc_ids_side_effects = self._paginated_requests_as_side_effects(
            ioc_ids_paginated_requests,
        )

        get_ioc_details_url = "iocs/entities/indicators/v1"

        # Mock the responses for getting ioc details.
        ioc_details_resources = [
            {"id": f"ioc-{i}", "value": "noname", "type": "md5"}
            for i in range(1, 7)
        ]
        # The ioc value to search. We expect to go through all data to find it.
        ioc_details_resources[-1]["value"] = "somevalue"

        ioc_details_requests = self._get_offset_paginated_requests(
            ioc_details_resources, page_size, page_size,
        )
        ioc_details_side_effects = self._paginated_requests_as_side_effects(
            ioc_details_requests,
        )

        # Combine the side effects for ioc IDs and ioc details.
        combined_side_effects = itertools.chain.from_iterable(
            zip(ioc_ids_side_effects, ioc_details_side_effects),
        )

        captured_calls = []

        side_effect = self.intercepting_side_effect_calls(
            captured_calls, combined_side_effects,
        )

        with patch.object(
            self.manager.session,
            "request",
            side_effect=side_effect,
        ) as mock_request:
            iocs = self.manager.get_uploaded_iocs(
                ioc_types=["md5"],
                ioc_value="somevalue",
                filter_strategy="Contains",
                page_size=page_size,
            )

        # Verify that one ioc is returned.
        assert len(iocs) == 1, "Should have returned 1 item."

        # Verify that the requests were made as expected.
        assert mock_request.call_count == 6, "Should have been called 6 times."
        expected_calls = [
            # ==== Pipeline Iteration 1 ====
            call(
                "GET",
                get_ioc_ids_url,
                params={"filter": "type:['md5']", "limit": page_size},
                json=None,
            ),
            call(
                "GET",
                get_ioc_details_url,
                params={"ids": ioc_ids_resources[0:2]},
                json=None,
            ),
            # ==== Pipeline Iteration 2 ====
            call(
                "GET",
                get_ioc_ids_url,
                params={
                    "filter": "type:['md5']", "limit": page_size, "after": "token_2",
                },
                json=None,
            ),
            call(
                "GET",
                get_ioc_details_url,
                params={"ids": ioc_ids_resources[2:4]},
                json=None,
            ),
            # ==== Pipeline Iteration 3 ====
            call(
                "GET",
                get_ioc_ids_url,
                params={
                    "filter": "type:['md5']", "limit": page_size, "after": "token_4",
                },
                json=None,
            ),
            call(
                "GET",
                get_ioc_details_url,
                params={"ids": ioc_ids_resources[4:6]},
                json=None,
            ),
        ]
        assert captured_calls == expected_calls

    def test_get_uploaded_iocs_filter_equal_no_unnecessary_calls(self):
        """Tests that no unnecessary API calls are made when using the 'Equal' filter for
        iocs.
        """
        page_size = 2
        limit = 1

        get_ioc_ids_url = "iocs/queries/indicators/v1"

        # Mock the responses for getting ioc IDs.
        ioc_ids_resources = [f"ioc-{i}" for i in range(1, 7)]
        ioc_ids_paginated_requests = self._get_token_paginated_requests(
            ioc_ids_resources, len(ioc_ids_resources), page_size,
        )
        ioc_ids_side_effects = self._paginated_requests_as_side_effects(
            ioc_ids_paginated_requests,
        )

        get_ioc_details_url = "iocs/entities/indicators/v1"

        # Mock the responses for getting ioc details.
        ioc_details_resources = [
            {"id": f"ioc-{i}", "value": "somevalue", "type": "md5"}
            for i in range(1, 7)
        ]

        ioc_details_requests = self._get_offset_paginated_requests(
            ioc_details_resources, page_size, page_size,
        )
        ioc_details_side_effects = self._paginated_requests_as_side_effects(
            ioc_details_requests,
        )

        # Combine the side effects for ioc IDs and ioc details.
        combined_side_effects = itertools.chain.from_iterable(
            zip(ioc_ids_side_effects, ioc_details_side_effects),
        )

        captured_calls = []

        side_effect = self.intercepting_side_effect_calls(
            captured_calls, combined_side_effects,
        )

        with patch.object(
            self.manager.session,
            "request",
            side_effect=side_effect,
        ) as mock_request:
            iocs = self.manager.get_uploaded_iocs(
                ioc_types=["md5"],
                ioc_value="somevalue",
                filter_strategy="Equal",
                limit=limit,
                page_size=page_size,
            )

        # Verify that one ioc is returned.
        assert len(iocs) == 1, "Should have returned 1 items."

        # Verify that only two API calls were made.
        assert mock_request.call_count == 2, "Should have 2 expected calls."

        expected_calls = [
            # ==== Pipeline Iteration 1 ====
            call(
                "GET",
                get_ioc_ids_url,
                params={
                    "filter": "type:['md5']+value:'somevalue'",
                    "limit": limit,
                },
                json=None,
            ),
            call(
                "GET",
                get_ioc_details_url,
                params={"ids": ioc_ids_resources[0:limit]},
                json=None,
            ),
        ]
        assert captured_calls == expected_calls

    @staticmethod
    def _get_token_paginated_requests(
        resources: list, total_items: int, pagination_step: int,
    ) -> list:
        """Creates a list of responses for token-paginated requests.

        Args:
            resources: A list of resources to be paginated.
            total_items: The total number of items in the paginated response.
            pagination_step: The number of items per page.

        Returns:
            A list of responses.
            Example of the data returned by `mock_response.json()`:
                {
                    "resources": ["item-1", "item-2"],
                    "meta": {"pagination": {"total": 2, "after": "next_token"}},
                }

        """
        return [
            {
                "resources": resources[i : i + pagination_step],
                "meta": {
                    "pagination": {
                        "total": total_items, "after": f"token_{i + pagination_step}",
                    },
                },
            }
            for i in range(0, len(resources), pagination_step)
        ]

    def test_token_pagination_generator_last_page_is_not_complete(self):
        """Tests the token pagination generator when the last page is not complete."""
        test_url = "test/endpoint"
        page_size = 2

        # Create a list of 5 resources to paginate through.
        resources = [f"item-{i}" for i in range(1, 6)]
        paginated_requests = self._get_token_paginated_requests(
            resources, len(resources), page_size,
        )
        side_effects = self._paginated_requests_as_side_effects(paginated_requests)

        captured_calls = []
        response_iterator = iter(side_effects)

        side_effect = self.intercepting_side_effect_calls(
            captured_calls, response_iterator,
        )

        with patch.object(
            self.manager.session,
            "request",
            side_effect=side_effect,
        ) as mock_request:
            pages_generator = self.manager.token_pagination_generator(
                url=test_url,
                page_size=page_size,
            )
            result_pages = list(pages_generator)

        # Verify that the generator yielded all 5 items.
        assert len(result_pages) == 5, "Should yield 5 items."
        # Verify that the request was called 3 times (2 full pages + 1 partial page).
        assert mock_request.call_count == 3, "Should have called 3 times."

        expected_calls = [
            call(
                "GET",
                test_url,
                params={"limit": page_size},
                json=None,
            ),
            call(
                "GET",
                test_url,
                params={"limit": page_size, "after": "token_2"},
                json=None,
            ),
            call(
                "GET",
                test_url,
                params={"limit": page_size, "after": "token_4"},
                json=None,
            ),
        ]
        assert captured_calls == expected_calls

    def test_token_pagination_generator_last_page_is_complete(self):
        """Tests the token pagination generator when the last page is complete."""
        test_url = "test/endpoint"
        page_size = 2

        # Create a list of 4 resources to paginate through.
        resources = [f"item-{i}" for i in range(1, 5)]
        paginated_requests = self._get_token_paginated_requests(
            resources, len(resources), page_size,
        )
        side_effects = self._paginated_requests_as_side_effects(paginated_requests)

        captured_calls = []
        response_iterator = iter(side_effects)

        side_effect = self.intercepting_side_effect_calls(
            captured_calls, response_iterator,
        )

        with patch.object(
            self.manager.session,
            "request",
            side_effect=side_effect,
        ) as mock_request:
            pages_generator = self.manager.token_pagination_generator(
                url=test_url,
                page_size=page_size,
            )
            result_pages = list(pages_generator)

        # Verify that the generator yielded all 4 items.
        assert len(result_pages) == 4, "Should yield 4 items."
        # Verify that the request was called 2 times (2 full pages).
        assert mock_request.call_count == 2, "Should have been called 2 times."

        expected_calls = [
            call(
                "GET",
                test_url,
                params={"limit": page_size},
                json=None,
            ),
            call(
                "GET",
                test_url,
                params={"limit": page_size, "after": "token_2"},
                json=None,
            ),
        ]
        assert captured_calls == expected_calls

    def test_token_pagination_generator_page_has_less_data_then_requested(self):
        """Tests the token pagination generator when a page has less data than
        requested.
        """
        test_url = "test/endpoint"
        page_size_param = 3

        # Create a list of 2 resources, which is less than the page size.
        page_1_resources = ["item-1", "item-2"]

        total_items = len(page_1_resources)
        paginated_requests = self._get_token_paginated_requests(
            page_1_resources, total_items, page_size_param,
        )
        side_effects = self._paginated_requests_as_side_effects(paginated_requests)

        captured_calls = []
        response_iterator = iter(side_effects)

        side_effect = self.intercepting_side_effect_calls(
            captured_calls, response_iterator,
        )

        with patch.object(
            self.manager.session,
            "request",
            side_effect=side_effect,
        ) as mock_request:
            pages_generator = self.manager.token_pagination_generator(
                url=test_url,
                page_size=page_size_param,
            )
            result_pages = list(pages_generator)

        # Verify that the generator yielded all 2 items.
        assert len(result_pages) == 2, "Should yield 2 items."

        # Verify that the request was called only once.
        assert mock_request.call_count == 1, "Should have been called 1 time."
        expected_calls = [
            call(
                "GET",
                test_url,
                params={"limit": page_size_param},
                json=None,
            ),
        ]
        assert captured_calls == expected_calls
