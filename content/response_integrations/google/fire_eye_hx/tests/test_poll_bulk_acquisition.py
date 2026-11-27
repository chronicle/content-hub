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

import copy
import unittest
from typing import Any
from unittest.mock import MagicMock, patch

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)

from ..actions import PollBulkAcquisition as poll_module
from ..core.FireEyeHXManager import (
    FireEyeHXManagerError,
    FireEyeHXNotFoundError,
)

NOW_MS: int = 1_700_000_000_000

SAMPLE_BULK_ACQUISITION: dict[str, Any] = {
    "_id": 1209,
    "state": "STOPPED",
    "scripts": [
        {
            "_id": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "url": "/hx/api/v3/scripts/xxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "download": "/hx/api/v3/scripts/xxxxxxxxxxxxxxxxxxxxxxxxxxxxx.xml",
            "platform": "win",
        }
    ],
    "comment": "",
    "update_time": "2026-11-16T11:06:50.811Z",
    "create_time": "2026-11-16T10:04:27.972Z",
    "update_actor": {"_id": 1006, "username": "user"},
    "create_actor": {"_id": 1006, "username": "user"},
    "max_size_in_mb": None,
    "_revision": "20261116110650811574390937",
    "disable_cef": False,
    "url": "/hx/api/v3/acqs/bulk/1209",
    "host_set": {"_id": 9, "url": "/hx/api/v3/host_sets/9", "name": "hosts"},
    "stats": {
        "total_size": 893,
        "run_time": {
            "avg": "116.4442040000000000",
            "min": "116.444204",
            "max": "116.444204",
        },
        "task_size": {
            "avg": "893.0000000000000000",
            "min": "893",
            "max": "893",
        },
        "running_state": {
            "NEW": 0,
            "QUEUED": 0,
            "FAILED": 0,
            "COMPLETE": 1,
            "ABORTED": 0,
            "DELETED": 0,
            "REFRESH": 0,
            "CANCELLED": 0,
        },
    },
}


def _make_action_param_side_effect(bulk_id: str) -> Any:
    def _side_effect(siemplify: Any, param_name: str, **kwargs: Any) -> Any:
        if param_name == "Bulk Acquisition ID":
            return bulk_id
        return kwargs.get("default_value")

    return _side_effect


class TestPollBulkAcquisition(unittest.TestCase):
    @patch.object(poll_module, "FireEyeHXManager")
    @patch.object(poll_module, "extract_action_param")
    @patch.object(poll_module, "extract_configuration_param")
    @patch.object(poll_module, "SiemplifyAction")
    def test_poll_in_progress_when_hosts_in_new_state(
        self,
        mock_siemplify_action: MagicMock,
        mock_extract_config: MagicMock,
        mock_extract_action: MagicMock,
        mock_manager_cls: MagicMock,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value
        mock_extract_action.side_effect = _make_action_param_side_effect("1209")

        payload = copy.deepcopy(SAMPLE_BULK_ACQUISITION)
        payload["state"] = "RUNNING"
        payload["stats"]["running_state"]["NEW"] = 2
        payload["stats"]["running_state"]["COMPLETE"] = 1
        mock_manager.get_bulk_acquisition.return_value = payload

        poll_module.main()

        mock_manager.get_bulk_acquisition.assert_called_once_with(1209)
        mock_siemplify.result.add_result_json.assert_not_called()
        mock_manager.logout.assert_called_once()
        end_args = mock_siemplify.end.call_args[0]
        self.assertIn("Waiting for results for the following bulk acquisition: 1209.", end_args[0])
        self.assertIn("NEW: 2, QUEUED: 0, REFRESH: 0", end_args[0])
        self.assertEqual(end_args[1], "false")
        self.assertEqual(end_args[2], EXECUTION_STATE_INPROGRESS)

    @patch.object(poll_module, "FireEyeHXManager")
    @patch.object(poll_module, "extract_action_param")
    @patch.object(poll_module, "extract_configuration_param")
    @patch.object(poll_module, "SiemplifyAction")
    def test_poll_in_progress_when_hosts_in_queued_state(
        self,
        mock_siemplify_action: MagicMock,
        mock_extract_config: MagicMock,
        mock_extract_action: MagicMock,
        mock_manager_cls: MagicMock,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value
        mock_extract_action.side_effect = _make_action_param_side_effect("1209")

        payload = copy.deepcopy(SAMPLE_BULK_ACQUISITION)
        payload["state"] = "RUNNING"
        payload["stats"]["running_state"]["QUEUED"] = 3
        mock_manager.get_bulk_acquisition.return_value = payload

        poll_module.main()

        mock_siemplify.result.add_result_json.assert_not_called()
        end_args = mock_siemplify.end.call_args[0]
        self.assertIn("Waiting for results for the following bulk acquisition: 1209.", end_args[0])
        self.assertIn("NEW: 0, QUEUED: 3, REFRESH: 0", end_args[0])
        self.assertEqual(end_args[1], "false")
        self.assertEqual(end_args[2], EXECUTION_STATE_INPROGRESS)

    @patch.object(poll_module, "FireEyeHXManager")
    @patch.object(poll_module, "extract_action_param")
    @patch.object(poll_module, "extract_configuration_param")
    @patch.object(poll_module, "SiemplifyAction")
    def test_poll_in_progress_when_hosts_in_refresh_state(
        self,
        mock_siemplify_action: MagicMock,
        mock_extract_config: MagicMock,
        mock_extract_action: MagicMock,
        mock_manager_cls: MagicMock,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value
        mock_extract_action.side_effect = _make_action_param_side_effect("1209")

        payload = copy.deepcopy(SAMPLE_BULK_ACQUISITION)
        payload["state"] = "RUNNING"
        payload["stats"]["running_state"]["REFRESH"] = 2
        payload["stats"]["running_state"]["COMPLETE"] = 1
        mock_manager.get_bulk_acquisition.return_value = payload

        poll_module.main()

        mock_siemplify.result.add_result_json.assert_not_called()
        end_args = mock_siemplify.end.call_args[0]
        self.assertIn("Waiting for results for the following bulk acquisition: 1209.", end_args[0])
        self.assertIn("Pending hosts: 2 (NEW: 0, QUEUED: 0, REFRESH: 2) out of 3", end_args[0])
        self.assertEqual(end_args[1], "false")
        self.assertEqual(end_args[2], EXECUTION_STATE_INPROGRESS)

    @patch.object(poll_module, "FireEyeHXManager")
    @patch.object(poll_module, "extract_action_param")
    @patch.object(poll_module, "extract_configuration_param")
    @patch.object(poll_module, "SiemplifyAction")
    def test_poll_in_progress_when_hosts_in_new_queued_and_refresh_states(
        self,
        mock_siemplify_action: MagicMock,
        mock_extract_config: MagicMock,
        mock_extract_action: MagicMock,
        mock_manager_cls: MagicMock,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value
        mock_extract_action.side_effect = _make_action_param_side_effect("1209")

        payload = copy.deepcopy(SAMPLE_BULK_ACQUISITION)
        payload["state"] = "RUNNING"
        payload["stats"]["running_state"]["NEW"] = 1
        payload["stats"]["running_state"]["QUEUED"] = 2
        payload["stats"]["running_state"]["REFRESH"] = 1
        payload["stats"]["running_state"]["FAILED"] = 1
        payload["stats"]["running_state"]["COMPLETE"] = 4
        mock_manager.get_bulk_acquisition.return_value = payload

        poll_module.main()

        mock_siemplify.result.add_result_json.assert_not_called()
        end_args = mock_siemplify.end.call_args[0]
        self.assertIn("Waiting for results for the following bulk acquisition: 1209.", end_args[0])
        self.assertIn("Pending hosts: 4 (NEW: 1, QUEUED: 2, REFRESH: 1) out of 9", end_args[0])
        self.assertEqual(end_args[1], "false")
        self.assertEqual(end_args[2], EXECUTION_STATE_INPROGRESS)

    @patch.object(poll_module, "FireEyeHXManager")
    @patch.object(poll_module, "extract_action_param")
    @patch.object(poll_module, "extract_configuration_param")
    @patch.object(poll_module, "SiemplifyAction")
    def test_poll_stops_when_all_hosts_not_in_new_queued_or_refresh_state(
        self,
        mock_siemplify_action: MagicMock,
        mock_extract_config: MagicMock,
        mock_extract_action: MagicMock,
        mock_manager_cls: MagicMock,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value
        mock_extract_action.side_effect = _make_action_param_side_effect("1209")

        payload = copy.deepcopy(SAMPLE_BULK_ACQUISITION)
        payload["state"] = "RUNNING"
        payload["stats"]["running_state"] = {
            "NEW": 0,
            "QUEUED": 0,
            "FAILED": 1,
            "COMPLETE": 2,
            "ABORTED": 1,
            "DELETED": 0,
            "REFRESH": 0,
            "CANCELLED": 1,
        }
        mock_manager.get_bulk_acquisition.return_value = payload

        poll_module.main()

        mock_siemplify.result.add_result_json.assert_called_once_with(payload)
        end_args = mock_siemplify.end.call_args[0]
        self.assertIn(
            'Successfully polled bulk acquisition with ID "1209" in FireEye HX. State: RUNNING.',
            end_args[0],
        )
        self.assertIn("no hosts remain in NEW, QUEUED, or REFRESH state", end_args[0])
        self.assertEqual(end_args[1], "true")
        self.assertEqual(end_args[2], EXECUTION_STATE_COMPLETED)

    @patch.object(poll_module, "FireEyeHXManager")
    @patch.object(poll_module, "extract_action_param")
    @patch.object(poll_module, "extract_configuration_param")
    @patch.object(poll_module, "SiemplifyAction")
    def test_poll_stops_when_running_state_counts_all_zero(
        self,
        mock_siemplify_action: MagicMock,
        mock_extract_config: MagicMock,
        mock_extract_action: MagicMock,
        mock_manager_cls: MagicMock,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value
        mock_extract_action.side_effect = _make_action_param_side_effect("1209")

        payload = copy.deepcopy(SAMPLE_BULK_ACQUISITION)
        payload["state"] = "RUNNING"
        payload["stats"]["running_state"] = {
            "NEW": 0,
            "QUEUED": 0,
            "FAILED": 0,
            "COMPLETE": 0,
            "ABORTED": 0,
            "DELETED": 0,
            "REFRESH": 0,
            "CANCELLED": 0,
        }
        mock_manager.get_bulk_acquisition.return_value = payload

        poll_module.main()

        mock_siemplify.result.add_result_json.assert_called_once_with(payload)
        end_args = mock_siemplify.end.call_args[0]
        self.assertIn(
            'Successfully polled bulk acquisition with ID "1209" in FireEye HX. State: RUNNING.',
            end_args[0],
        )
        self.assertIn("no target hosts were reported for the bulk acquisition", end_args[0])
        self.assertEqual(end_args[1], "true")
        self.assertEqual(end_args[2], EXECUTION_STATE_COMPLETED)

    @patch.object(poll_module, "FireEyeHXManager")
    @patch.object(poll_module, "extract_action_param")
    @patch.object(poll_module, "extract_configuration_param")
    @patch.object(poll_module, "SiemplifyAction")
    def test_poll_stops_when_running_state_is_empty_dict(
        self,
        mock_siemplify_action: MagicMock,
        mock_extract_config: MagicMock,
        mock_extract_action: MagicMock,
        mock_manager_cls: MagicMock,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value
        mock_extract_action.side_effect = _make_action_param_side_effect("1209")

        payload = {"_id": 1209, "state": "RUNNING", "stats": {"running_state": {}}}
        mock_manager.get_bulk_acquisition.return_value = payload

        poll_module.main()

        mock_siemplify.result.add_result_json.assert_called_once_with(payload)
        end_args = mock_siemplify.end.call_args[0]
        self.assertIn(
            'Successfully polled bulk acquisition with ID "1209" in FireEye HX. State: RUNNING.',
            end_args[0],
        )
        self.assertIn("no target hosts were reported for the bulk acquisition", end_args[0])
        self.assertEqual(end_args[1], "true")
        self.assertEqual(end_args[2], EXECUTION_STATE_COMPLETED)

    @patch.object(poll_module, "FireEyeHXManager")
    @patch.object(poll_module, "extract_action_param")
    @patch.object(poll_module, "extract_configuration_param")
    @patch.object(poll_module, "SiemplifyAction")
    def test_poll_stops_when_stats_is_null(
        self,
        mock_siemplify_action: MagicMock,
        mock_extract_config: MagicMock,
        mock_extract_action: MagicMock,
        mock_manager_cls: MagicMock,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value
        mock_extract_action.side_effect = _make_action_param_side_effect("1209")

        payload: dict[str, Any] = {"_id": 1209, "state": "RUNNING", "stats": None}
        mock_manager.get_bulk_acquisition.return_value = payload

        poll_module.main()

        mock_siemplify.result.add_result_json.assert_called_once_with(payload)
        end_args = mock_siemplify.end.call_args[0]
        self.assertIn(
            'Successfully polled bulk acquisition with ID "1209" in FireEye HX. State: RUNNING.',
            end_args[0],
        )
        self.assertIn("no target hosts were reported for the bulk acquisition", end_args[0])
        self.assertEqual(end_args[1], "true")
        self.assertEqual(end_args[2], EXECUTION_STATE_COMPLETED)

    @patch.object(poll_module, "FireEyeHXManager")
    @patch.object(poll_module, "extract_action_param")
    @patch.object(poll_module, "extract_configuration_param")
    @patch.object(poll_module, "SiemplifyAction")
    def test_poll_stops_when_bulk_acquisition_in_stopped_state_sample_payload(
        self,
        mock_siemplify_action: MagicMock,
        mock_extract_config: MagicMock,
        mock_extract_action: MagicMock,
        mock_manager_cls: MagicMock,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value
        mock_extract_action.side_effect = _make_action_param_side_effect("1209")

        payload = copy.deepcopy(SAMPLE_BULK_ACQUISITION)
        mock_manager.get_bulk_acquisition.return_value = payload

        poll_module.main()

        mock_siemplify.result.add_result_json.assert_called_once_with(payload)
        end_args = mock_siemplify.end.call_args[0]
        self.assertIn(
            'Successfully polled bulk acquisition with ID "1209" in FireEye HX. State: STOPPED.',
            end_args[0],
        )
        self.assertIn("STOPPED state", end_args[0])
        self.assertEqual(end_args[1], "true")
        self.assertEqual(end_args[2], EXECUTION_STATE_COMPLETED)

    @patch.object(poll_module, "FireEyeHXManager")
    @patch.object(poll_module, "extract_action_param")
    @patch.object(poll_module, "extract_configuration_param")
    @patch.object(poll_module, "SiemplifyAction")
    def test_poll_stops_when_stopped_even_with_new_queued_and_refresh_hosts(
        self,
        mock_siemplify_action: MagicMock,
        mock_extract_config: MagicMock,
        mock_extract_action: MagicMock,
        mock_manager_cls: MagicMock,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value
        mock_extract_action.side_effect = _make_action_param_side_effect("1209")

        payload = copy.deepcopy(SAMPLE_BULK_ACQUISITION)
        payload["state"] = "STOPPED"
        payload["stats"]["running_state"]["NEW"] = 5
        payload["stats"]["running_state"]["QUEUED"] = 3
        payload["stats"]["running_state"]["REFRESH"] = 2
        mock_manager.get_bulk_acquisition.return_value = payload

        poll_module.main()

        mock_siemplify.result.add_result_json.assert_called_once_with(payload)
        end_args = mock_siemplify.end.call_args[0]
        self.assertIn(
            'Successfully polled bulk acquisition with ID "1209" in FireEye HX. State: STOPPED.',
            end_args[0],
        )
        self.assertIn("STOPPED state", end_args[0])
        self.assertEqual(end_args[1], "true")
        self.assertEqual(end_args[2], EXECUTION_STATE_COMPLETED)

    @patch.object(poll_module, "FireEyeHXManager")
    @patch.object(poll_module, "extract_action_param")
    @patch.object(poll_module, "extract_configuration_param")
    @patch.object(poll_module, "SiemplifyAction")
    def test_poll_fails_when_bulk_acquisition_not_found(
        self,
        mock_siemplify_action: MagicMock,
        mock_extract_config: MagicMock,
        mock_extract_action: MagicMock,
        mock_manager_cls: MagicMock,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value
        mock_extract_action.side_effect = _make_action_param_side_effect("9999")
        mock_manager.get_bulk_acquisition.side_effect = FireEyeHXNotFoundError(
            "Unable to fetch status for bulk acquisition 9999: Not Found"
        )

        poll_module.main()

        mock_manager.get_bulk_acquisition.assert_called_once_with(9999)
        mock_siemplify.result.add_result_json.assert_not_called()
        mock_manager.logout.assert_called_once()
        mock_siemplify.end.assert_called_once_with(
            'Error executing action "Poll Bulk Acquisition". Reason: '
            'Bulk acquisition with ID "9999" was not found in FireEye HX.',
            "false",
            EXECUTION_STATE_FAILED,
        )

    @patch.object(poll_module, "FireEyeHXManager")
    @patch.object(poll_module, "extract_action_param")
    @patch.object(poll_module, "extract_configuration_param")
    @patch.object(poll_module, "SiemplifyAction")
    def test_poll_fails_when_bulk_acquisition_payload_empty(
        self,
        mock_siemplify_action: MagicMock,
        mock_extract_config: MagicMock,
        mock_extract_action: MagicMock,
        mock_manager_cls: MagicMock,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value
        mock_extract_action.side_effect = _make_action_param_side_effect("1209")
        mock_manager.get_bulk_acquisition.return_value = {}

        poll_module.main()

        mock_siemplify.result.add_result_json.assert_not_called()
        mock_siemplify.end.assert_called_once_with(
            'Error executing action "Poll Bulk Acquisition". Reason: '
            'Empty response returned when fetching bulk acquisition with ID "1209" from FireEye HX.',
            "false",
            EXECUTION_STATE_FAILED,
        )

    @patch.object(poll_module, "FireEyeHXManager")
    @patch.object(poll_module, "extract_action_param")
    @patch.object(poll_module, "extract_configuration_param")
    @patch.object(poll_module, "SiemplifyAction")
    def test_poll_empty_id_failure(
        self,
        mock_siemplify_action: MagicMock,
        mock_extract_config: MagicMock,
        mock_extract_action: MagicMock,
        mock_manager_cls: MagicMock,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value
        mock_extract_action.side_effect = _make_action_param_side_effect("")

        poll_module.main()

        mock_manager_cls.assert_not_called()
        mock_manager.get_bulk_acquisition.assert_not_called()
        end_args = mock_siemplify.end.call_args[0]
        self.assertTrue(end_args[0].startswith('Error executing action "Poll Bulk Acquisition". Reason: '))
        self.assertIn("must not be empty", end_args[0])
        self.assertEqual(end_args[1], "false")
        self.assertEqual(end_args[2], EXECUTION_STATE_FAILED)

    @patch.object(poll_module, "FireEyeHXManager")
    @patch.object(poll_module, "extract_action_param")
    @patch.object(poll_module, "extract_configuration_param")
    @patch.object(poll_module, "SiemplifyAction")
    def test_poll_non_numeric_id_failure(
        self,
        mock_siemplify_action: MagicMock,
        mock_extract_config: MagicMock,
        mock_extract_action: MagicMock,
        mock_manager_cls: MagicMock,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value
        mock_extract_action.side_effect = _make_action_param_side_effect("bad_input_abc")

        poll_module.main()

        mock_manager_cls.assert_not_called()
        mock_manager.get_bulk_acquisition.assert_not_called()
        end_args = mock_siemplify.end.call_args[0]
        self.assertTrue(end_args[0].startswith('Error executing action "Poll Bulk Acquisition". Reason: '))
        self.assertIn("must be a number", end_args[0])
        self.assertEqual(end_args[1], "false")
        self.assertEqual(end_args[2], EXECUTION_STATE_FAILED)

    @patch.object(poll_module, "FireEyeHXManager")
    @patch.object(poll_module, "extract_action_param")
    @patch.object(poll_module, "extract_configuration_param")
    @patch.object(poll_module, "SiemplifyAction")
    def test_poll_api_error_failure(
        self,
        mock_siemplify_action: MagicMock,
        mock_extract_config: MagicMock,
        mock_extract_action: MagicMock,
        mock_manager_cls: MagicMock,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value
        mock_extract_action.side_effect = _make_action_param_side_effect("1209")
        mock_manager.get_bulk_acquisition.side_effect = FireEyeHXManagerError("HTTP 500 Internal Server Error")

        poll_module.main()

        mock_manager.logout.assert_called_once()
        mock_siemplify.result.add_result_json.assert_not_called()
        end_args = mock_siemplify.end.call_args[0]
        self.assertTrue(end_args[0].startswith('Error executing action "Poll Bulk Acquisition". Reason: '))
        self.assertIn("HTTP 500 Internal Server Error", end_args[0])
        self.assertEqual(end_args[1], "false")
        self.assertEqual(end_args[2], EXECUTION_STATE_FAILED)

    @patch.object(poll_module, "FireEyeHXManager")
    @patch.object(poll_module, "extract_action_param")
    @patch.object(poll_module, "extract_configuration_param")
    @patch.object(poll_module, "SiemplifyAction")
    def test_poll_manager_init_not_found_fails_instead_of_completing(
        self,
        mock_siemplify_action: MagicMock,
        mock_extract_config: MagicMock,
        mock_extract_action: MagicMock,
        mock_manager_cls: MagicMock,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_extract_action.side_effect = _make_action_param_side_effect("1209")
        mock_manager_cls.side_effect = FireEyeHXNotFoundError("Unable to obtain token: 404")

        poll_module.main()

        end_args = mock_siemplify.end.call_args[0]
        self.assertTrue(end_args[0].startswith('Error executing action "Poll Bulk Acquisition". Reason: '))
        self.assertIn("Unable to obtain token", end_args[0])
        self.assertEqual(end_args[1], "false")
        self.assertEqual(end_args[2], EXECUTION_STATE_FAILED)

    @patch.object(poll_module, "FireEyeHXManager")
    @patch.object(poll_module, "extract_action_param")
    @patch.object(poll_module, "extract_configuration_param")
    @patch.object(poll_module, "SiemplifyAction")
    def test_poll_logout_error_does_not_fail_completed_action(
        self,
        mock_siemplify_action: MagicMock,
        mock_extract_config: MagicMock,
        mock_extract_action: MagicMock,
        mock_manager_cls: MagicMock,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value
        mock_extract_action.side_effect = _make_action_param_side_effect("1209")
        mock_manager.get_bulk_acquisition.return_value = copy.deepcopy(SAMPLE_BULK_ACQUISITION)
        mock_manager.logout.side_effect = RuntimeError("logout failed")

        poll_module.main()

        mock_siemplify.LOGGER.warn.assert_called_once()
        end_args = mock_siemplify.end.call_args[0]
        self.assertIn(
            'Successfully polled bulk acquisition with ID "1209" in FireEye HX. State: STOPPED.',
            end_args[0],
        )
        self.assertEqual(end_args[1], "true")
        self.assertEqual(end_args[2], EXECUTION_STATE_COMPLETED)

    @patch.object(poll_module, "unix_now", return_value=NOW_MS)
    @patch.object(poll_module, "FireEyeHXManager")
    @patch.object(poll_module, "extract_action_param")
    @patch.object(poll_module, "extract_configuration_param")
    @patch.object(poll_module, "SiemplifyAction")
    def test_poll_fails_when_execution_deadline_approaching_and_hosts_pending(
        self,
        mock_siemplify_action: MagicMock,
        mock_extract_config: MagicMock,
        mock_extract_action: MagicMock,
        mock_manager_cls: MagicMock,
        _mock_unix_now: MagicMock,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_siemplify.async_total_duration_deadline = 0
        mock_siemplify.execution_deadline_unix_time_ms = NOW_MS + 30_000
        mock_manager = mock_manager_cls.return_value
        mock_extract_action.side_effect = _make_action_param_side_effect("1209")

        payload = copy.deepcopy(SAMPLE_BULK_ACQUISITION)
        payload["state"] = "RUNNING"
        payload["stats"]["running_state"]["NEW"] = 2
        payload["stats"]["running_state"]["QUEUED"] = 1
        payload["stats"]["running_state"]["COMPLETE"] = 1
        mock_manager.get_bulk_acquisition.return_value = payload

        poll_module.main()

        mock_siemplify.result.add_result_json.assert_not_called()
        mock_manager.logout.assert_called_once()
        mock_siemplify.end.assert_called_once_with(
            'Error executing action "Poll Bulk Acquisition". Reason: '
            "action ran into a timeout during execution. "
            "Pending bulk acquisition: 1209 (3 pending hosts out of 4). "
            "Please increase the timeout in IDE and try again.",
            "false",
            EXECUTION_STATE_FAILED,
        )

    @patch.object(poll_module, "unix_now", return_value=NOW_MS)
    @patch.object(poll_module, "FireEyeHXManager")
    @patch.object(poll_module, "extract_action_param")
    @patch.object(poll_module, "extract_configuration_param")
    @patch.object(poll_module, "SiemplifyAction")
    def test_poll_fails_when_async_total_duration_deadline_approaching_and_hosts_pending(
        self,
        mock_siemplify_action: MagicMock,
        mock_extract_config: MagicMock,
        mock_extract_action: MagicMock,
        mock_manager_cls: MagicMock,
        _mock_unix_now: MagicMock,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_siemplify.async_total_duration_deadline = NOW_MS + 10_000
        mock_siemplify.execution_deadline_unix_time_ms = NOW_MS + 600_000
        mock_manager = mock_manager_cls.return_value
        mock_extract_action.side_effect = _make_action_param_side_effect("1209")

        payload = copy.deepcopy(SAMPLE_BULK_ACQUISITION)
        payload["state"] = "RUNNING"
        payload["stats"]["running_state"]["NEW"] = 1
        payload["stats"]["running_state"]["COMPLETE"] = 1
        mock_manager.get_bulk_acquisition.return_value = payload

        poll_module.main()

        mock_siemplify.result.add_result_json.assert_not_called()
        mock_siemplify.end.assert_called_once_with(
            'Error executing action "Poll Bulk Acquisition". Reason: '
            "action ran into a timeout during execution. "
            "Pending bulk acquisition: 1209 (1 pending hosts out of 2). "
            "Please increase the timeout in IDE and try again.",
            "false",
            EXECUTION_STATE_FAILED,
        )

    @patch.object(poll_module, "unix_now", return_value=NOW_MS)
    @patch.object(poll_module, "FireEyeHXManager")
    @patch.object(poll_module, "extract_action_param")
    @patch.object(poll_module, "extract_configuration_param")
    @patch.object(poll_module, "SiemplifyAction")
    def test_poll_completes_even_when_timeout_approaching_if_acquisition_finished(
        self,
        mock_siemplify_action: MagicMock,
        mock_extract_config: MagicMock,
        mock_extract_action: MagicMock,
        mock_manager_cls: MagicMock,
        _mock_unix_now: MagicMock,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_siemplify.async_total_duration_deadline = NOW_MS + 5_000
        mock_manager = mock_manager_cls.return_value
        mock_extract_action.side_effect = _make_action_param_side_effect("1209")

        payload = copy.deepcopy(SAMPLE_BULK_ACQUISITION)
        payload["state"] = "RUNNING"
        mock_manager.get_bulk_acquisition.return_value = payload

        poll_module.main()

        mock_siemplify.result.add_result_json.assert_called_once_with(payload)
        end_args = mock_siemplify.end.call_args[0]
        self.assertIn("no hosts remain in NEW, QUEUED, or REFRESH state", end_args[0])
        self.assertEqual(end_args[1], "true")
        self.assertEqual(end_args[2], EXECUTION_STATE_COMPLETED)

    @patch.object(poll_module, "unix_now", return_value=NOW_MS)
    @patch.object(poll_module, "FireEyeHXManager")
    @patch.object(poll_module, "extract_action_param")
    @patch.object(poll_module, "extract_configuration_param")
    @patch.object(poll_module, "SiemplifyAction")
    def test_poll_stays_in_progress_when_deadline_not_approaching(
        self,
        mock_siemplify_action: MagicMock,
        mock_extract_config: MagicMock,
        mock_extract_action: MagicMock,
        mock_manager_cls: MagicMock,
        _mock_unix_now: MagicMock,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_siemplify.async_total_duration_deadline = NOW_MS + 300_000
        mock_manager = mock_manager_cls.return_value
        mock_extract_action.side_effect = _make_action_param_side_effect("1209")

        payload = copy.deepcopy(SAMPLE_BULK_ACQUISITION)
        payload["state"] = "RUNNING"
        payload["stats"]["running_state"]["QUEUED"] = 2
        mock_manager.get_bulk_acquisition.return_value = payload

        poll_module.main()

        mock_siemplify.result.add_result_json.assert_not_called()
        end_args = mock_siemplify.end.call_args[0]
        self.assertIn("Waiting for results for the following bulk acquisition: 1209.", end_args[0])
        self.assertEqual(end_args[1], "false")
        self.assertEqual(end_args[2], EXECUTION_STATE_INPROGRESS)


if __name__ == "__main__":
    unittest.main()
