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

import unittest
from unittest.mock import MagicMock, patch

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyDataModel import EntityTypes

from trend_vision_one.actions import (
    AddEntityToBlocklist,
    RemoveEntityFromBlocklist,
)
from trend_vision_one.actions.AddEntityToBlocklist import (
    query_operation_status,
    start_operation,
)
from trend_vision_one.core.datamodels import BlocklistResponse, TaskDetail
from trend_vision_one.core.TrendVisionOneExceptions import TrendVisionOneTimeoutException
from trend_vision_one.core.TrendVisionOneParser import TrendVisionOneParser
from trend_vision_one.core.UtilsManager import build_blocklist_payloads as _build_payloads


class MockEntity:
    def __init__(self, identifier: str, entity_type: Any) -> None:
        self.identifier = identifier
        self.entity_type = entity_type
        self.additional_properties: dict[str, Any] = {}
        self.is_enriched = False


class TestBlocklistActions(unittest.TestCase):
    def test_build_payloads_deduplication_and_normalization(self) -> None:
        siemplify = MagicMock()
        siemplify.parameters = {
            "File Hashes": "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855",
            "URLs": "https://malicious.example.com",
            "Domains": "malicious.example.com",
            "Email Addresses": "attacker@evil.com",
            "IPs": "192.168.1.1",
        }

        with patch(
            "trend_vision_one.core.UtilsManager.extract_action_param",
            side_effect=lambda action, param_name, **kwargs: siemplify.parameters.get(param_name, ""),
        ):
            entities = [
                MockEntity("192.168.1.1", EntityTypes.ADDRESS),
                MockEntity("malicious.example.com", EntityTypes.HOSTNAME),
                MockEntity("attacker@evil.com", EntityTypes.USER),
                MockEntity("DA39A3EE5E6B4B0D3255BFEF95601890AFD80709", EntityTypes.FILEHASH),
            ]

            objects, _entity_map = _build_payloads(siemplify, entities)

            # 192.168.1.1 entity and parameter should be deduplicated to only 1 payload item
            ip_objs = [obj for obj in objects if "ip" in obj]
            assert len(ip_objs) == 1
            assert ip_objs[0]["ip"] == "192.168.1.1"

            # Check SHA1 and SHA256 hashes are lowercased
            sha1_obj = next(obj for obj in objects if "fileSha1" in obj)
            assert sha1_obj["fileSha1"] == "da39a3ee5e6b4b0d3255bfef95601890afd80709"
            sha256_obj = next(obj for obj in objects if "fileSha256" in obj)
            assert sha256_obj["fileSha256"] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_parser_blocklist_response_case_insensitive_header_and_dict(self) -> None:
        parser = TrendVisionOneParser()

        # Multi-status item with mixed-case Operation-Location in list headers
        raw_list = {
            "status": 201,
            "headers": [
                {"name": "OPERATION-LOCATION", "value": "https://api.xdr.trendmicro.com/v3.0/response/tasks/task-12345"}
            ],
            "body": {},
        }
        res = parser.build_blocklist_response_object(raw_list)
        assert res.id == "task-12345"
        assert res.url == "https://api.xdr.trendmicro.com/v3.0/response/tasks/task-12345"
        assert res.error_message is None

        # Dict headers support
        raw_dict = {
            "status": 201,
            "headers": {"Operation-Location": "https://api.xdr.trendmicro.com/v3.0/response/tasks/task-67890"},
            "body": {},
        }
        res_dict = parser.build_blocklist_response_object(raw_dict)
        assert res_dict.id == "task-67890"
        assert res_dict.url == "https://api.xdr.trendmicro.com/v3.0/response/tasks/task-67890"

        # Multi-status item with error
        raw_error = {
            "status": 400,
            "body": {"error": {"code": "InvalidFormat", "message": "The IP address format is invalid."}},
        }
        res_err = parser.build_blocklist_response_object(raw_error)
        assert res_err.id is None
        assert res_err.error_message == "The IP address format is invalid."

    def test_manager_single_dict_and_list_response(self) -> None:
        parser = TrendVisionOneParser()

        # Single dict response (e.g. error from gateway)
        single_dict = {"status": 400, "body": {"error": {"message": "Bad request"}}}
        raw_response = single_dict
        if isinstance(raw_response, dict):
            raw_response = [raw_response]
        parsed = [parser.build_blocklist_response_object(item) for item in raw_response]
        assert len(parsed) == 1
        assert parsed[0].error_message == "Bad request"

    def test_start_operation_and_async_polling_with_uppercase_hash(self) -> None:
        siemplify = MagicMock()
        siemplify.execution_deadline_unix_time_ms = 1000000000000
        siemplify.parameters = {
            "File Hashes": "",
            "URLs": "",
            "Domains": "",
            "Email Addresses": "",
            "IPs": "10.0.0.1",
        }
        upper_hash_entity = MockEntity("DA39A3EE5E6B4B0D3255BFEF95601890AFD80709", EntityTypes.FILEHASH)
        siemplify.target_entities = [MockEntity("10.0.0.1", EntityTypes.ADDRESS), upper_hash_entity]

        manager = MagicMock()
        manager.add_entities_to_blocklist.return_value = [
            BlocklistResponse(raw_data={}, task_id="task-1", url="https://api/tasks/task-1"),
            BlocklistResponse(raw_data={}, task_id="task-2", url="https://api/tasks/task-2"),
        ]
        # In progress on first poll
        manager.get_task.return_value = TaskDetail(
            raw_data={}, task_id="task-1", action="addCustomScript", status="running"
        )

        result_data = {}
        with (
            patch(
                "trend_vision_one.core.UtilsManager.extract_action_param",
                side_effect=lambda action, param_name, **kwargs: siemplify.parameters.get(param_name, ""),
            ),
            patch("trend_vision_one.core.UtilsManager.is_async_action_global_timeout_approaching", return_value=False),
            patch("trend_vision_one.core.UtilsManager.is_approaching_timeout", return_value=False),
        ):
            _msg, _res, status = start_operation(siemplify, manager, 1000, siemplify.target_entities, result_data)

            assert status == EXECUTION_STATE_INPROGRESS
            assert "task-1" in result_data["result_urls"]["10.0.0.1"]

            # Second poll: tasks succeeded
            manager.get_task.return_value = TaskDetail(
                raw_data={}, task_id="task-1", action="addCustomScript", status="succeeded"
            )
            _msg2, res2, status2 = query_operation_status(siemplify, manager, result_data, 1000)

            assert status2 == EXECUTION_STATE_COMPLETED
            assert res2
            assert "10.0.0.1" in result_data["completed"]
            assert siemplify.target_entities[0].additional_properties.get("TrendVisionOne_in_blocklist") is True
            # Verify uppercase hash was successfully enriched
            assert upper_hash_entity.is_enriched is True
            assert upper_hash_entity.additional_properties.get("TrendVisionOne_in_blocklist") is True

    def test_remove_entity_from_blocklist(self) -> None:
        siemplify = MagicMock()
        siemplify.execution_deadline_unix_time_ms = 1000000000000
        siemplify.parameters = {
            "File Hashes": "",
            "URLs": "",
            "Domains": "example.com",
            "Email Addresses": "",
            "IPs": "",
        }
        domain_entity = MockEntity("example.com", EntityTypes.HOSTNAME)
        siemplify.target_entities = [domain_entity]

        manager = MagicMock()
        manager.remove_entities_from_blocklist.return_value = [
            BlocklistResponse(raw_data={}, task_id="task-rem-1", url="https://api/tasks/task-rem-1")
        ]
        manager.get_task.return_value = TaskDetail(
            raw_data={}, task_id="task-rem-1", action="removeCustomScript", status="succeeded"
        )

        result_data = {}
        with (
            patch(
                "trend_vision_one.core.UtilsManager.extract_action_param",
                side_effect=lambda action, param_name, **kwargs: siemplify.parameters.get(param_name, ""),
            ),
            patch("trend_vision_one.core.UtilsManager.is_async_action_global_timeout_approaching", return_value=False),
            patch("trend_vision_one.core.UtilsManager.is_approaching_timeout", return_value=False),
        ):
            _msg, res, status = RemoveEntityFromBlocklist.start_operation(
                siemplify, manager, 1000, siemplify.target_entities, result_data
            )

            assert status == EXECUTION_STATE_COMPLETED
            assert res is True
            assert "example.com" in result_data["completed"]
            assert domain_entity.is_enriched is True
            assert domain_entity.additional_properties.get("TrendVisionOne_in_blocklist") is False

    def test_task_failed_and_rejected_handling(self) -> None:
        siemplify = MagicMock()
        siemplify.execution_deadline_unix_time_ms = 1000000000000
        siemplify.parameters = {"File Hashes": "", "URLs": "", "Domains": "", "Email Addresses": "", "IPs": "10.0.0.2"}
        ip_entity = MockEntity("10.0.0.2", EntityTypes.ADDRESS)
        siemplify.target_entities = [ip_entity]

        manager = MagicMock()
        manager.add_entities_to_blocklist.return_value = [
            BlocklistResponse(raw_data={}, task_id="task-failed-1", url="https://api/tasks/task-failed-1")
        ]
        manager.get_task.return_value = TaskDetail(
            raw_data={}, task_id="task-failed-1", action="addCustomScript", status="failed"
        )

        result_data = {}
        with (
            patch(
                "trend_vision_one.core.UtilsManager.extract_action_param",
                side_effect=lambda action, param_name, **kwargs: siemplify.parameters.get(param_name, ""),
            ),
            patch("trend_vision_one.core.UtilsManager.is_async_action_global_timeout_approaching", return_value=False),
            patch("trend_vision_one.core.UtilsManager.is_approaching_timeout", return_value=False),
        ):
            _msg, res, status = start_operation(siemplify, manager, 1000, siemplify.target_entities, result_data)

            assert status == EXECUTION_STATE_COMPLETED
            assert res is False
            assert "10.0.0.2" in result_data["failed"]
            assert ip_entity.is_enriched is False

    def test_timeout_handling(self) -> None:
        siemplify = MagicMock()
        siemplify.execution_deadline_unix_time_ms = 1000000000000
        siemplify.parameters = {"File Hashes": "", "URLs": "", "Domains": "", "Email Addresses": "", "IPs": "10.0.0.3"}
        siemplify.target_entities = [MockEntity("10.0.0.3", EntityTypes.ADDRESS)]

        manager = MagicMock()
        manager.add_entities_to_blocklist.return_value = [
            BlocklistResponse(raw_data={}, task_id="task-timeout", url="https://api/tasks/task-timeout")
        ]

        result_data = {}
        with (
            patch(
                "trend_vision_one.core.UtilsManager.extract_action_param",
                side_effect=lambda action, param_name, **kwargs: siemplify.parameters.get(param_name, ""),
            ),
            patch("trend_vision_one.core.UtilsManager.is_async_action_global_timeout_approaching", return_value=True),
            self.assertRaises(TrendVisionOneTimeoutException),
        ):
            start_operation(siemplify, manager, 1000, siemplify.target_entities, result_data)


if __name__ == "__main__":
    unittest.main()
