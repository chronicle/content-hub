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
import abc
import dataclasses
import uuid
from typing import Any


@dataclasses.dataclass
class TenableIOProduct(abc.ABC):
    """A mock product simulating the Tenable.io backend service.

    This class acts as a mock database, holding the state of assets,
    vulnerabilities, policies, scanners, and scans for integration tests.
    """

    assets: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    vulnerabilities: dict[str, list[dict[str, Any]]] = dataclasses.field(
        default_factory=dict
    )
    policies: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    scanners: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    scans: dict[str, dict[str, Any]] = dataclasses.field(default_factory=dict)

    def add_asset(self, asset: dict[str, Any]) -> None:
        """Adds a new asset to the mock database.

        Args:
            asset (dict[str, Any]): The asset data to add.
        """
        self.assets.append(asset)

    def add_vulnerabilities(
        self, asset_id: str, vulns: list[dict[str, Any]]
    ) -> None:
        """Adds a list of vulnerabilities for a specific asset.

        Args:
            asset_id (str): The ID of the asset to associate the vulns with.
            vulns (list[dict[str, Any]]): A list of vulnerability data.
        """
        self.vulnerabilities[asset_id] = vulns

    def add_policy(self, policy: dict[str, Any]) -> None:
        """Adds a new scan policy to the mock database.

        Args:
            policy (dict[str, Any]): The policy data to add.
        """
        self.policies.append(policy)

    def add_scanner(self, scanner: dict[str, Any]) -> None:
        """Adds a new scanner to the mock database.

        Args:
            scanner (dict[str, Any]): The scanner data to add.
        """
        self.scanners.append(scanner)

    def get_all_assets(self) -> list[dict[str, Any]]:
        """Retrieves all assets from the mock database.

        Returns:
            list[dict[str, Any]]: A list of all stored assets.
        """
        return self.assets

    def get_asset_by_id(self, asset_id: str) -> dict[str, Any] | None:
        """Finds a single asset by its ID.

        Args:
            asset_id (str): The ID of the asset to find.

        Returns:
            dict[str, Any] | None: The asset data if found, otherwise None.
        """
        for asset in self.assets:
            if asset.get("id") == asset_id:
                return asset
        return None

    def get_vulnerabilities(self, asset_id: str) -> list[dict[str, Any]]:
        """Retrieves vulnerabilities for a specific asset.

        Args:
            asset_id (str): The ID of the asset.

        Returns:
            list[dict[str, Any]]: A list of vulnerabilities, or an empty
                list if none are found.
        """
        return self.vulnerabilities.get(asset_id, [])

    def get_policies(self) -> list[dict[str, Any]]:
        """Retrieves all scan policies.

        Returns:
            list[dict[str, Any]]: A list of all stored policies.
        """
        return self.policies

    def get_scanners(self) -> list[dict[str, Any]]:
        """Retrieves all scanners.

        Returns:
            list[dict[str, Any]]: A list of all stored scanners.
        """
        return self.scanners

    def create_scan(self, scan_data: dict[str, Any]) -> str:
        """Creates a new scan record in the mock product.

        This method simulates the creation of a scan by generating a unique
        scan ID, setting an initial status, and storing the scan data.

        Args:
            scan_data (dict[str, Any]): The payload containing the scan details.

        Returns:
            str: The unique ID generated for the new scan.
        """
        scan_id = str(uuid.uuid4())
        scan_data["id"] = scan_id
        scan_data["status"] = "empty"
        self.scans[scan_id] = scan_data
        return scan_id

    def update_scan_status(self, scan_id: str, status: str) -> None:
        """Updates the status of an existing scan.

        Args:
            scan_id (str): The ID of the scan to update.
            status (str): The new status to set (e.g., "running", "completed").
        """
        if scan_id in self.scans:
            self.scans[scan_id]["status"] = status

    def get_scan(self, scan_id: str) -> dict[str, Any] | None:
        """Retrieves a scan record by its ID.

        Args:
            scan_id (str): The ID of the scan to retrieve.

        Returns:
            dict[str, Any] | None: The scan data if found, otherwise None.
        """
        return self.scans.get(scan_id)
