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

from ..core.FireEyeHXManager import FireEyeHXManager


class TestFireEyeHXManagerBulk(unittest.TestCase):
    def setUp(self) -> None:
        self.raw_api_root = "https://fireeye.example.com"
        with patch.object(FireEyeHXManager, "get_token", return_value="fake_token"):
            self.manager = FireEyeHXManager(
                api_root=self.raw_api_root,
                username="test_user",
                password="test_password",
                verify_ssl=False,
            )
        self.api_root = self.manager.api_root
        self.mock_session = MagicMock()
        self.mock_session.headers = {}
        self.manager.session = self.mock_session

    def test_get_host_sets(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "entries": [
                    {"_id": 9, "name": "all_hosts"},
                    {"_id": 10, "name": "windows_hosts"},
                ]
            }
        }
        mock_response.status_code = 200
        self.mock_session.get.return_value = mock_response

        entries = self.manager.get_host_sets(name="all_hosts", limit=10)

        self.mock_session.get.assert_called_once_with(
            f"{self.api_root}/host_sets",
            params={"name": "all_hosts", "limit": 10},
        )
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["_id"], 9)

    def test_get_host_set_id_by_name_found(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "entries": [
                    {"_id": 15, "name": "MD Hunt Endpoints"},
                ]
            }
        }
        mock_response.status_code = 200
        self.mock_session.get.return_value = mock_response

        resolved_id = self.manager.get_host_set_id_by_name("md hunt endpoints")
        self.assertEqual(resolved_id, 15)

    def test_get_host_set_id_by_name_not_found(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "entries": [
                    {"_id": 15, "name": "Other Host Set"},
                ]
            }
        }
        mock_response.status_code = 200
        self.mock_session.get.return_value = mock_response

        resolved_id = self.manager.get_host_set_id_by_name("non_existent_set")
        self.assertIsNone(resolved_id)

    def test_get_host_set_id_by_name_skips_invalid_entries(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "entries": [
                    {"name": "target_set"},  # missing _id
                    {"_id": None, "name": "target_set"},  # None _id
                    {"_id": "not_an_int", "name": "target_set"},  # invalid _id
                    {"_id": "25", "name": "target_set"},  # valid string int
                ]
            }
        }
        mock_response.status_code = 200
        self.mock_session.get.return_value = mock_response

        resolved_id = self.manager.get_host_set_id_by_name("target_set")
        self.assertEqual(resolved_id, 25)

    def test_get_host_set_id_by_name_empty(self) -> None:
        resolved_id = self.manager.get_host_set_id_by_name("")
        self.assertIsNone(resolved_id)
        self.mock_session.get.assert_not_called()

    def test_create_bulk_acquisition_with_agent_ids(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"_id": 101, "state": "QUEUED"}}
        mock_response.status_code = 200
        self.mock_session.post.return_value = mock_response

        result = self.manager.create_bulk_acquisition(
            script_b64="PHNjcmlwdD48L3NjcmlwdD4=",
            agent_ids=["agent-1", "agent-2"],
            comment="Test comment",
        )

        self.mock_session.post.assert_called_once_with(
            f"{self.api_root}/acqs/bulk",
            json={
                "script": {"b64": "PHNjcmlwdD48L3NjcmlwdD4="},
                "comment": "Test comment",
                "hosts": [{"_id": "agent-1"}, {"_id": "agent-2"}],
            },
        )
        self.assertEqual(result["_id"], 101)

    def test_create_bulk_acquisition_with_host_set_id(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"_id": 102, "state": "RUNNING"}}
        mock_response.status_code = 200
        self.mock_session.post.return_value = mock_response

        result = self.manager.create_bulk_acquisition(
            script_b64="PHNjcmlwdD48L3NjcmlwdD4=",
            host_set_id=42,
        )

        self.mock_session.post.assert_called_once_with(
            f"{self.api_root}/acqs/bulk",
            json={
                "script": {"b64": "PHNjcmlwdD48L3NjcmlwdD4="},
                "host_set": {"_id": 42},
            },
        )
        self.assertEqual(result["_id"], 102)

    def test_create_bulk_acquisition_no_target_raises_value_error(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.manager.create_bulk_acquisition(script_b64="PHNjcmlwdD48L3NjcmlwdD4=")
        self.assertIn("Either agent_ids or host_set_id must be provided", str(ctx.exception))
        self.mock_session.post.assert_not_called()

    def test_get_bulk_acquisition(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"_id": 42, "state": "RUNNING"}}
        mock_response.status_code = 200
        self.mock_session.get.return_value = mock_response

        result = self.manager.get_bulk_acquisition(42)

        self.mock_session.get.assert_called_once_with(f"{self.api_root}/acqs/bulk/42")
        self.assertEqual(result["_id"], 42)

    def test_stop_bulk_acquisition(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        self.mock_session.post.return_value = mock_response

        result = self.manager.stop_bulk_acquisition(42)

        self.mock_session.post.assert_called_once_with(f"{self.api_root}/acqs/bulk/42/actions/stop")
        self.assertTrue(result)

    def test_delete_bulk_acquisition(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        self.mock_session.delete.return_value = mock_response

        result = self.manager.delete_bulk_acquisition(42)

        self.mock_session.delete.assert_called_once_with(f"{self.api_root}/acqs/bulk/42")
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
