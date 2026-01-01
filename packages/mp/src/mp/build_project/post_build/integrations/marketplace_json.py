"""Utilities for generating the marketplace JSON file.

This module provides functionality to traverse integration directories,
read their definition files, and compile them into a comprehensive
`marketplace.json` file. It also includes checks for duplicate
integration identifiers within a marketplace.
"""

# Copyright 2025 Google LLC
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

import dataclasses
import json
from typing import TYPE_CHECKING, NamedTuple

import mp.core.constants
import mp.core.file_utils
import mp.core.utils
from mp.core.data_models.common.release_notes.metadata import ReleaseNote
from mp.core.data_models.integrations.connector.metadata import ConnectorMetadata

from .data_models import FullDetailsExtraAttrs

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

    from mp.core.custom_types import Products
    from mp.core.data_models.integrations.action.metadata import BuiltActionMetadata

    from .data_models import BuiltFullDetailsIntegrationMetadata, BuiltSupportedAction


SECONDS_IN_MINUTE: int = 60
MINUTES_IN_HOUR: int = 60
HOURS_IN_DAY: int = 24
SECONDS_IN_DAY: int = SECONDS_IN_MINUTE * MINUTES_IN_HOUR * HOURS_IN_DAY
DAY_IN_MILLISECONDS: int = mp.core.constants.MS_IN_SEC * SECONDS_IN_DAY
UPDATE_NOTIFICATIONS_DAYS: int = 4
NEW_NOTIFICATION_DAYS: int = 30


class DuplicateIntegrationIdentifierInMarketplaceError(Exception):
    """When a marketplace (community/commercial) contains duplicate integration IDs."""


class ReleaseTimes(NamedTuple):
    """Release Time parameters."""

    latest_release: int | None
    update_notification: int | None
    new_notification: int | None


def write_marketplace_json(dst: Path) -> None:
    """Write the marketplace JSON file to a path.

    Args:
        dst: destination path to write the marketplace JSON into

    Raises:
        DuplicateIntegrationIdentifierInMarketplaceError:
            when multiple integrations with the same name were added to the
            `marketplace.json` file

    """
    products: Products[set[Path]] = mp.core.file_utils.get_integrations_and_groups_from_paths(dst)
    identifiers: set[str] = set()
    duplicates: list[tuple[str, str]] = []
    def_files: list[BuiltFullDetailsIntegrationMetadata] = []
    for i in products.integrations:
        mjd: MarketplaceJsonDefinition = MarketplaceJsonDefinition(i)
        def_file_path: Path = i / mp.core.constants.INTEGRATION_DEF_FILE.format(i.name)
        def_file: BuiltFullDetailsIntegrationMetadata = mjd.get_def_file(def_file_path)

        identifier: str = def_file["Identifier"]
        if identifier in identifiers:
            duplicates.append((identifier, def_file["DisplayName"]))

        identifiers.add(identifier)
        def_files.append(def_file)

    if duplicates:
        names: str = "\n".join(f"Identifier: {d[0]}, DisplayName: {d[1]}" for d in duplicates)
        msg: str = f"The following integrations have duplicates: {names}"
        raise DuplicateIntegrationIdentifierInMarketplaceError(msg)

    marketplace_json: Path = dst / mp.core.constants.MARKETPLACE_JSON_NAME
    marketplace_json.write_text(json.dumps(def_files, sort_keys=True, indent=4), encoding="UTF-8")


@dataclasses.dataclass(slots=True, frozen=True)
class MarketplaceJsonDefinition:
    integration_path: Path

    def get_def_file(self, def_file_path: Path) -> BuiltFullDetailsIntegrationMetadata:
        """Get an integration's marketplace JSON definition.

        Args:
            def_file_path: The integration's `.def` file's path

        Returns:
            An integrations built version of the marketplace JSON definition

        """
        metadata: BuiltFullDetailsIntegrationMetadata = json.loads(
            def_file_path.read_text(encoding="utf-8")
        )
        self._update_full_details_with_extra_attrs(metadata)
        return metadata

    def _update_full_details_with_extra_attrs(
        self,
        metadata: BuiltFullDetailsIntegrationMetadata,
    ) -> None:
        release_times: ReleaseTimes = self._get_integration_release_time()
        has_connectors: bool = self._has_connectors()
        supported_actions: list[BuiltSupportedAction] = self._get_supported_actions()
        extra_attrs: FullDetailsExtraAttrs = FullDetailsExtraAttrs(
            HasConnectors=has_connectors,
            SupportedActions=supported_actions,
            LatestReleasePublishTimeUnixTime=release_times.latest_release,
            UpdateNotificationExpired=release_times.update_notification,
            NewNotificationExpired=release_times.new_notification,
        )
        metadata.update(extra_attrs)  # type: ignore[typeddict-item]
        mp.core.utils.remove_none_entries_from_mapping(metadata)

    def _get_integration_release_time(self) -> ReleaseTimes:
        release_notes: Sequence[ReleaseNote] = ReleaseNote.from_built_path(self.integration_path)
        latest_release_time: int | None = _get_latest_release_time(release_notes)
        if latest_release_time is None or latest_release_time < 0:
            return ReleaseTimes(None, None, None)

        update_notification: int = _get_update_notification_time(latest_release_time)
        new_notification: int = _get_new_notification_time(latest_release_time)
        return ReleaseTimes(latest_release_time, update_notification, new_notification)

    def _has_connectors(self) -> bool:
        return any(ConnectorMetadata.from_built_path(self.integration_path))

    def _get_supported_actions(self) -> list[BuiltSupportedAction]:
        actions_definitions: Path = self.integration_path / mp.core.constants.OUT_ACTIONS_META_DIR
        if not actions_definitions.exists():
            return []

        supported_action: list[BuiltSupportedAction] = []
        for action_meta_path in actions_definitions.iterdir():
            action_meta: BuiltActionMetadata = json.loads(
                action_meta_path.read_text(encoding="utf-8")
            )
            supported_action.append(
                {
                    "Name": action_meta["Name"],
                    "Description": action_meta["Description"],
                },
            )

        return supported_action


def _get_latest_release_time(release_notes: Iterable[ReleaseNote]) -> int | None:
    if not release_notes:
        return 0

    latest_version: float = max(float(rn.version) for rn in release_notes)
    latest_version_rn: list[ReleaseNote] = [
        rn for rn in release_notes if rn.version == latest_version
    ]
    if not latest_version:
        return None

    return latest_version_rn[0].publish_time


def _get_update_notification_time(latest_release_time: int) -> int:
    release_time_ms: int = latest_release_time * mp.core.constants.MS_IN_SEC
    expiration_delta_ms: int = UPDATE_NOTIFICATIONS_DAYS * DAY_IN_MILLISECONDS
    return release_time_ms + expiration_delta_ms


def _get_new_notification_time(latest_release_time: int) -> int:
    release_time_ms: int = latest_release_time * mp.core.constants.MS_IN_SEC
    expiration_delta_ms: int = NEW_NOTIFICATION_DAYS * DAY_IN_MILLISECONDS
    return expiration_delta_ms + release_time_ms
