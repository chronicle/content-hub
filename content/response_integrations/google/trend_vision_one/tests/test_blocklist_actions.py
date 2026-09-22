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

import json
import unittest
from typing import Any
from unittest.mock import MagicMock, patch

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyDataModel import EntityTypes

from trend_vision_one.actions.AddEntityToBlocklist import AddEntityToBlocklist
from trend_vision_one.actions.RemoveEntityFromBlocklist import (
    RemoveEntityFromBlocklist,
)
from trend_vision_one.core.datamodels import BlocklistResponse, TaskDetail
from trend_vision_one.core.TrendVisionOneManager import TrendVisionOneManager
from trend_vision_one.core.TrendVisionOneParser import TrendVisionOneParser
from trend_vision_one.core.UtilsManager import (
    build_blocklist_payloads as _build_payloads,
)


class MockEntity:
    """Lightweight mock representing a Chronicle DomainEntityInfo object."""

    def __init__(self, identifier: str, entity_type: str) -> None:
        """Initialize MockEntity with an identifier and Chronicle entity type."""
        self.identifier = identifier
        self.entity_type = entity_type
        self.additional_properties: dict[str, Any] = {}
        self.is_enriched = False


def _create_action_instance(
    action_cls: type[AddEntityToBlocklist | RemoveEntityFromBlocklist],
    siemplify: MagicMock,
    manager: MagicMock,
) -> AddEntityToBlocklist | RemoveEntityFromBlocklist:
    """Instantiate a blocklist action class wired to mocked Siemplify and Manager objects."""
    with patch("trend_vision_one.core.base_action.SiemplifyAction", return_value=siemplify):
        action = action_cls()
    action.api_client = manager
    action.action_start_time = 1000
    action.params = {
        "description": siemplify.parameters.get("Description"),
        "additional_data": siemplify.parameters.get("additional_data", "{}"),
    }
    return action


class TestBlocklistActions(unittest.TestCase):
    """Unit tests for Trend Vision One AddEntityToBlocklist and RemoveEntityFromBlocklist actions."""

    def test_build_payloads_deduplication_and_normalization(self) -> None:
        """Verify payload deduplication, DOMAIN/HOSTNAME mapping, and hex hash validation."""
        siemplify = MagicMock()
        siemplify.parameters = {
            "File Hashes": (
                "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855, "
                "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"
            ),
            "URLs": "https://malicious.example.com",
            "Domains": "malicious.example.com",
            "Email Addresses": "attacker@evil.com, invalid-email",
            "IPs": "192.168.1.1",
        }

        with patch(
            "trend_vision_one.core.UtilsManager.extract_action_param",
            side_effect=lambda action, param_name, **kwargs: siemplify.parameters.get(
                param_name, ""
            ),
        ):
            entities = [
                MockEntity("192.168.1.1", EntityTypes.ADDRESS),
                MockEntity("malicious.example.com", EntityTypes.HOSTNAME),
                MockEntity("sub.evil.example.com", EntityTypes.DOMAIN),
                MockEntity("attacker@evil.com", EntityTypes.USER),
                MockEntity(
                    "DA39A3EE5E6B4B0D3255BFEF95601890AFD80709", EntityTypes.FILEHASH
                ),
                MockEntity(
                    "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG", EntityTypes.FILEHASH
                ),
            ]

            objects, entity_map = _build_payloads(siemplify, entities)

            # 192.168.1.1 entity and parameter should be deduplicated to only 1 payload item
            ip_objs = [obj for obj in objects if "ip" in obj]
            assert len(ip_objs) == 1
            assert ip_objs[0]["ip"] == "192.168.1.1"

            # Both HOSTNAME and DOMAIN entities map to 'domain'
            domain_objs = [obj["domain"] for obj in objects if "domain" in obj]
            assert domain_objs == ["malicious.example.com", "sub.evil.example.com"]

            # Valid SHA1 and SHA256 hashes are lowercased, while non-hex 40-char strings are rejected
            sha1_objs = [obj for obj in objects if "fileSha1" in obj]
            assert len(sha1_objs) == 1
            assert (
                sha1_objs[0]["fileSha1"]
                == "da39a3ee5e6b4b0d3255bfef95601890afd80709"
            )
            assert (
                entity_map["da39a3ee5e6b4b0d3255bfef95601890afd80709"]
                == "DA39A3EE5E6B4B0D3255BFEF95601890AFD80709"
            )
            sha256_objs = [obj for obj in objects if "fileSha256" in obj]
            assert len(sha256_objs) == 1
            assert (
                sha256_objs[0]["fileSha256"]
                == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            )

    def test_parser_blocklist_response_case_insensitive_header_and_dict(self) -> None:
        """Verify case-insensitive Operation-Location header extraction for list and dict formats."""
        parser = TrendVisionOneParser()

        raw_list = {
            "status": 201,
            "headers": [
                {
                    "name": "OPERATION-LOCATION",
                    "value": "https://api.xdr.trendmicro.com/v3.0/response/tasks/task-12345",
                }
            ],
            "body": {},
        }
        res = parser.build_blocklist_response_object(raw_list)
        assert res.id == "task-12345"
        assert (
            res.url == "https://api.xdr.trendmicro.com/v3.0/response/tasks/task-12345"
        )
        assert res.error_message is None

        raw_dict = {
            "status": 201,
            "headers": {
                "Operation-Location": "https://api.xdr.trendmicro.com/v3.0/response/tasks/task-67890"
            },
            "body": {},
        }
        res_dict = parser.build_blocklist_response_object(raw_dict)
        assert res_dict.id == "task-67890"
        assert (
            res_dict.url
            == "https://api.xdr.trendmicro.com/v3.0/response/tasks/task-67890"
        )

        raw_error = {
            "status": 400,
            "body": {
                "error": {
                    "code": "InvalidFormat",
                    "message": "The IP address format is invalid.",
                }
            },
        }
        res_err = parser.build_blocklist_response_object(raw_error)
        assert res_err.id is None
        assert res_err.error_message == "The IP address format is invalid."

    def test_manager_resolve_task_url_relative_and_id(self) -> None:
        """Verify TrendVisionOneManager.resolve_task_url handles full URLs, relative paths, and IDs."""
        with patch("trend_vision_one.core.TrendVisionOneManager.requests.Session"):
            mgr = TrendVisionOneManager(
                api_root="https://api.xdr.trendmicro.com",
                api_token=str(12345),
                verify_ssl=True,
            )

            assert (
                mgr.resolve_task_url(
                    "https://api.xdr.trendmicro.com/v3.0/response/tasks/task-1"
                )
                == "https://api.xdr.trendmicro.com/v3.0/response/tasks/task-1"
            )
            assert (
                mgr.resolve_task_url("/v3.0/response/tasks/task-2")
                == "https://api.xdr.trendmicro.com/v3.0/response/tasks/task-2"
            )
            assert (
                mgr.resolve_task_url("task-3")
                == "https://api.xdr.trendmicro.com/v3.0/response/tasks/task-3"
            )

    def test_manager_single_dict_and_list_response(self) -> None:
        """Verify a single-object error response for a multi-item batch marks all items failed."""
        siemplify = MagicMock()
        siemplify.execution_deadline_unix_time_ms = 1000000000000
        siemplify.parameters = {
            "File Hashes": "",
            "URLs": "",
            "Domains": "",
            "Email Addresses": "",
            "IPs": "10.0.0.1, 10.0.0.2, 10.0.0.3",
            "Description": "Batch block",
        }
        siemplify.target_entities = []

        manager = MagicMock()
        manager.add_entities_to_blocklist.return_value = [
            BlocklistResponse(raw_data={}, error_message="Bad request")
        ]

        action = _create_action_instance(AddEntityToBlocklist, siemplify, manager)
        with patch(
            "trend_vision_one.core.UtilsManager.extract_action_param",
            side_effect=lambda act, param_name, **kwargs: siemplify.parameters.get(
                param_name, ""
            ),
        ):
            action._perform_action(0)
            assert action.execution_state == EXECUTION_STATE_COMPLETED
            assert action.result_value is False
            assert len(action.result_data["failed"]) == 3
            assert set(action.result_data["failed"]) == {
                "10.0.0.1",
                "10.0.0.2",
                "10.0.0.3",
            }
            siemplify.update_entities.assert_not_called()

    def test_start_operation_and_async_polling_with_uppercase_hash(self) -> None:
        """Verify async polling and original uppercase SHA1 identifier preservation."""
        siemplify = MagicMock()
        siemplify.execution_deadline_unix_time_ms = 1000000000000
        siemplify.parameters = {
            "File Hashes": "",
            "URLs": "",
            "Domains": "",
            "Email Addresses": "",
            "IPs": "10.0.0.1",
        }
        upper_hash_entity = MockEntity(
            "DA39A3EE5E6B4B0D3255BFEF95601890AFD80709", EntityTypes.FILEHASH
        )
        siemplify.target_entities = [
            MockEntity("10.0.0.1", EntityTypes.ADDRESS),
            upper_hash_entity,
        ]

        manager = MagicMock()
        manager.add_entities_to_blocklist.return_value = [
            BlocklistResponse(
                raw_data={}, task_id="task-1", url="https://api/tasks/task-1"
            ),
            BlocklistResponse(
                raw_data={}, task_id="task-2", url="https://api/tasks/task-2"
            ),
        ]
        manager.get_task_by_id_or_url.return_value = TaskDetail(
            raw_data={}, task_id="task-1", action="addCustomScript", status="running"
        )

        action = _create_action_instance(AddEntityToBlocklist, siemplify, manager)
        with (
            patch(
                "trend_vision_one.core.UtilsManager.extract_action_param",
                side_effect=lambda act, param_name, **kwargs: siemplify.parameters.get(
                    param_name, ""
                ),
            ),
            patch(
                "trend_vision_one.core.base_action.is_async_action_global_timeout_approaching",
                return_value=False,
            ),
            patch(
                "trend_vision_one.core.base_action.is_approaching_timeout",
                return_value=False,
            ),
        ):
            action._perform_action(0)

            assert action.execution_state == EXECUTION_STATE_INPROGRESS
            assert (
                action.result_data["result_urls"]["10.0.0.1"]
                == "https://api/tasks/task-1"
            )
            assert (
                action.result_data["result_urls"][
                    "DA39A3EE5E6B4B0D3255BFEF95601890AFD80709"
                ]
                == "https://api/tasks/task-2"
            )

            # Second poll: tasks succeeded
            manager.get_task_by_id_or_url.return_value = TaskDetail(
                raw_data={},
                task_id="task-1",
                action="addCustomScript",
                status="succeeded",
            )
            action.params["additional_data"] = json.dumps(action.result_data)
            action._perform_action(1)

            assert action.execution_state == EXECUTION_STATE_COMPLETED
            assert action.result_value is True
            assert action.result_data["completed"] == [
                "10.0.0.1",
                "DA39A3EE5E6B4B0D3255BFEF95601890AFD80709",
            ]
            assert (
                siemplify.target_entities[0].additional_properties.get(
                    "TrendVisionOne_in_blocklist"
                )
                is True
            )
            assert upper_hash_entity.is_enriched is True
            assert (
                upper_hash_entity.additional_properties.get(
                    "TrendVisionOne_in_blocklist"
                )
                is True
            )

    def test_remove_entity_from_blocklist(self) -> None:
        """Verify RemoveEntityFromBlocklist sets TrendVisionOne_in_blocklist to False."""
        siemplify = MagicMock()
        siemplify.execution_deadline_unix_time_ms = 1000000000000
        siemplify.parameters = {
            "File Hashes": "",
            "URLs": "",
            "Domains": "example.com",
            "Email Addresses": "",
            "IPs": "",
        }
        domain_entity = MockEntity("example.com", EntityTypes.DOMAIN)
        siemplify.target_entities = [domain_entity]

        manager = MagicMock()
        manager.remove_entities_from_blocklist.return_value = [
            BlocklistResponse(
                raw_data={}, task_id="task-rem-1", url="https://api/tasks/task-rem-1"
            )
        ]
        manager.get_task_by_id_or_url.return_value = TaskDetail(
            raw_data={},
            task_id="task-rem-1",
            action="removeCustomScript",
            status="succeeded",
        )

        action = _create_action_instance(RemoveEntityFromBlocklist, siemplify, manager)
        with (
            patch(
                "trend_vision_one.core.UtilsManager.extract_action_param",
                side_effect=lambda act, param_name, **kwargs: siemplify.parameters.get(
                    param_name, ""
                ),
            ),
            patch(
                "trend_vision_one.core.base_action.is_async_action_global_timeout_approaching",
                return_value=False,
            ),
            patch(
                "trend_vision_one.core.base_action.is_approaching_timeout",
                return_value=False,
            ),
        ):
            action._perform_action(0)

            assert action.execution_state == EXECUTION_STATE_COMPLETED
            assert action.result_value is True
            assert action.result_data["completed"] == ["example.com"]
            assert domain_entity.is_enriched is True
            assert (
                domain_entity.additional_properties.get("TrendVisionOne_in_blocklist")
                is False
            )

    def test_task_failed_and_rejected_handling(self) -> None:
        """Verify tasks that finish with failed status mark the entity as failed without enriching."""
        siemplify = MagicMock()
        siemplify.execution_deadline_unix_time_ms = 1000000000000
        siemplify.parameters = {
            "File Hashes": "",
            "URLs": "",
            "Domains": "",
            "Email Addresses": "",
            "IPs": "10.0.0.2",
        }
        ip_entity = MockEntity("10.0.0.2", EntityTypes.ADDRESS)
        siemplify.target_entities = [ip_entity]

        manager = MagicMock()
        manager.add_entities_to_blocklist.return_value = [
            BlocklistResponse(
                raw_data={},
                task_id="task-failed-1",
                url="https://api/tasks/task-failed-1",
            )
        ]
        manager.get_task_by_id_or_url.return_value = TaskDetail(
            raw_data={},
            task_id="task-failed-1",
            action="addCustomScript",
            status="failed",
        )

        action = _create_action_instance(AddEntityToBlocklist, siemplify, manager)
        with (
            patch(
                "trend_vision_one.core.UtilsManager.extract_action_param",
                side_effect=lambda act, param_name, **kwargs: siemplify.parameters.get(
                    param_name, ""
                ),
            ),
            patch(
                "trend_vision_one.core.base_action.is_async_action_global_timeout_approaching",
                return_value=False,
            ),
            patch(
                "trend_vision_one.core.base_action.is_approaching_timeout",
                return_value=False,
            ),
        ):
            action._perform_action(0)

            assert action.execution_state == EXECUTION_STATE_COMPLETED
            assert action.result_value is False
            assert action.result_data["failed"] == ["10.0.0.2"]
            assert ip_entity.is_enriched is False
            siemplify.update_entities.assert_not_called()

    def test_timeout_handling(self) -> None:
        """Verify timeout sets EXECUTION_STATE_FAILED, enriches completed entities, and records JSON."""
        siemplify = MagicMock()
        siemplify.execution_deadline_unix_time_ms = 1000000000000
        siemplify.parameters = {
            "File Hashes": "",
            "URLs": "",
            "Domains": "",
            "Email Addresses": "",
            "IPs": "10.0.0.3, 10.0.0.4",
        }
        entity_completed = MockEntity("10.0.0.3", EntityTypes.ADDRESS)
        entity_pending = MockEntity("10.0.0.4", EntityTypes.ADDRESS)
        siemplify.target_entities = [entity_completed, entity_pending]

        manager = MagicMock()
        manager.add_entities_to_blocklist.return_value = [
            BlocklistResponse(raw_data={}, is_success=True),
            BlocklistResponse(
                raw_data={},
                task_id="task-timeout",
                url="https://api/tasks/task-timeout",
            ),
        ]

        action = _create_action_instance(AddEntityToBlocklist, siemplify, manager)
        with (
            patch(
                "trend_vision_one.core.UtilsManager.extract_action_param",
                side_effect=lambda act, param_name, **kwargs: siemplify.parameters.get(
                    param_name, ""
                ),
            ),
            patch(
                "trend_vision_one.core.base_action.is_async_action_global_timeout_approaching",
                return_value=True,
            ),
        ):
            action._perform_action(0)
            assert action.execution_state == EXECUTION_STATE_FAILED
            assert action.result_value is False
            assert action.output_message.startswith(
                'Error executing action "Add Entity To Blocklist". Reason:'
            )
            assert "Pending tasks" in action.output_message
            assert entity_completed.is_enriched is True
            assert entity_pending.is_enriched is False
            siemplify.update_entities.assert_called_once_with([entity_completed])

    def test_synchronous_success_and_non_running_terminal_and_exception_resilience(
        self,
    ) -> None:
        """Verify 204 synchronous completion, cancelled task status, and polling exception resilience."""
        parser = TrendVisionOneParser()
        sync_raw = {"status": 204, "headers": [], "body": {}}
        sync_res = parser.build_blocklist_response_object(sync_raw)
        assert sync_res.is_success is True
        assert sync_res.error_message is None

        siemplify = MagicMock()
        siemplify.execution_deadline_unix_time_ms = 1000000000000
        siemplify.parameters = {
            "File Hashes": "",
            "URLs": "",
            "Domains": "",
            "Email Addresses": "",
            "IPs": "10.0.0.10, 10.0.0.11, 10.0.0.12",
        }
        entity_sync = MockEntity("10.0.0.10", EntityTypes.ADDRESS)
        entity_cancelled = MockEntity("10.0.0.11", EntityTypes.ADDRESS)
        entity_exception = MockEntity("10.0.0.12", EntityTypes.ADDRESS)
        siemplify.target_entities = [entity_sync, entity_cancelled, entity_exception]

        manager = MagicMock()
        manager.add_entities_to_blocklist.return_value = [
            BlocklistResponse(raw_data={}, is_success=True),
            BlocklistResponse(
                raw_data={},
                task_id="task-cancel",
                url="https://api/tasks/task-cancel",
                is_success=True,
            ),
            BlocklistResponse(
                raw_data={},
                task_id="task-exc",
                url="https://api/tasks/task-exc",
                is_success=True,
            ),
        ]

        def get_task_side_effect(task_ref: str) -> TaskDetail:
            if task_ref == "https://api/tasks/task-cancel":
                return TaskDetail(
                    raw_data={},
                    task_id="task-cancel",
                    action="block",
                    status="cancelled",
                )
            raise RuntimeError

        manager.get_task_by_id_or_url.side_effect = get_task_side_effect

        action = _create_action_instance(AddEntityToBlocklist, siemplify, manager)
        with (
            patch(
                "trend_vision_one.core.UtilsManager.extract_action_param",
                side_effect=lambda act, param_name, **kwargs: siemplify.parameters.get(
                    param_name, ""
                ),
            ),
            patch(
                "trend_vision_one.core.base_action.is_async_action_global_timeout_approaching",
                return_value=False,
            ),
            patch(
                "trend_vision_one.core.base_action.is_approaching_timeout",
                return_value=False,
            ),
        ):
            action._perform_action(0)
            assert action.execution_state == EXECUTION_STATE_COMPLETED
            assert action.result_value is False
            assert action.result_data["completed"] == ["10.0.0.10"]
            assert entity_sync.is_enriched is True
            assert action.result_data["failed"] == ["10.0.0.11", "10.0.0.12"]
            siemplify.update_entities.assert_called_once_with([entity_sync])
            siemplify.result.add_result_json.assert_called_once()


if __name__ == "__main__":
    unittest.main()
