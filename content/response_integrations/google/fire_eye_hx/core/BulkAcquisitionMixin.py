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

from typing import Any


class BulkAcquisitionMixin:
    """Mixin providing bulk acquisition operations for FireEyeHXManager."""

    def get_host_sets(self, name: str | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        """Get list of host sets from FireEye HX.

        Args:
            name: Optional host set name filter.
            limit: Optional maximum number of records to return.

        Returns:
            List of host set entries.
        """
        url = f"{self.api_root}/host_sets"
        params: dict[str, str | int] = {}
        if name:
            params["name"] = name
        if limit:
            params["limit"] = limit
        response = self.session.get(url, params=params)
        self.validate_response(response, "Error getting host sets")
        return response.json().get("data", {}).get("entries", [])

    def get_host_set_id_by_name(self, host_set_name: str) -> int | None:
        """Resolve host set ID by name.

        Args:
            host_set_name: Name of host set (e.g. 'all_hosts').

        Returns:
            Host set numeric ID if found, or None.
        """
        if not host_set_name:
            return None
        entries = self.get_host_sets(name=host_set_name)
        for hs in entries:
            if "_id" not in hs or hs["_id"] is None:
                continue
            try:
                if str(hs.get("name", "")).lower() == host_set_name.lower():
                    return int(hs["_id"])
            except (ValueError, TypeError):
                continue
        return None

    def create_bulk_acquisition(
        self,
        script_b64: str,
        host_set_id: int | None = None,
        agent_ids: list[str] | None = None,
        comment: str | None = None,
    ) -> dict[str, Any]:
        """Create a bulk acquisition across endpoints.

        Args:
            script_b64: Base64-encoded XML or JSON script.
            host_set_id: Optional host set numeric ID.
            agent_ids: Optional list of target agent IDs.
            comment: Optional audit comment.

        Returns:
            Created bulk acquisition data object.

        Raises:
            ValueError: If neither agent_ids nor host_set_id is provided.
        """
        url = f"{self.api_root}/acqs/bulk"
        payload: dict[str, Any] = {
            "script": {"b64": script_b64},
        }
        if comment:
            payload["comment"] = comment

        if agent_ids:
            payload["hosts"] = [{"_id": aid.strip()} for aid in agent_ids]
        elif host_set_id is not None:
            payload["host_set"] = {"_id": host_set_id}
        else:
            raise ValueError("Either agent_ids or host_set_id must be provided.")

        response = self.session.post(url, json=payload)
        self.validate_response(response, "Error creating bulk acquisition")
        return response.json().get("data", {})

    def get_bulk_acquisition(self, bulk_acquisition_id: str | int) -> dict[str, Any]:
        """Get details and progress of a bulk acquisition.

        Args:
            bulk_acquisition_id: Bulk acquisition ID.

        Returns:
            Bulk acquisition data object.
        """
        url = f"{self.api_root}/acqs/bulk/{bulk_acquisition_id}"
        response = self.session.get(url)
        self.validate_response(response, f"Unable to fetch status for bulk acquisition {bulk_acquisition_id}")
        return response.json().get("data", {})

    def stop_bulk_acquisition(self, bulk_acquisition_id: str | int) -> bool:
        """Stop an active bulk acquisition.

        Args:
            bulk_acquisition_id: Bulk acquisition ID.

        Returns:
            True if successfully stopped.
        """
        url = f"{self.api_root}/acqs/bulk/{bulk_acquisition_id}/actions/stop"
        response = self.session.post(url)
        self.validate_response(response, f"Unable to stop bulk acquisition {bulk_acquisition_id}")
        return True

    def delete_bulk_acquisition(self, bulk_acquisition_id: str | int) -> bool:
        """Delete a bulk acquisition.

        Args:
            bulk_acquisition_id: Bulk acquisition ID.

        Returns:
            True if successfully deleted.
        """
        url = f"{self.api_root}/acqs/bulk/{bulk_acquisition_id}"
        response = self.session.delete(url)
        self.validate_response(response, f"Unable to delete bulk acquisition {bulk_acquisition_id}")
        return True
