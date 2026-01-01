"""Module for restructuring an integration's metadata.

This module defines a class, `Metadata`, responsible for organizing and
writing the various metadata files associated with an integration to its
designated output directory. This includes the main integration definition,
release notes, and metadata for actions, connectors, jobs, widgets, custom
families, and mapping rules.
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
import operator
from typing import TYPE_CHECKING

import mp.core.constants

from .restructurable import Restructurable

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from mp.core.data_models.common.release_notes.metadata import BuiltReleaseNote
    from mp.core.data_models.integrations.action.metadata import BuiltActionMetadata
    from mp.core.data_models.integrations.action_widget.metadata import BuiltActionWidgetMetadata
    from mp.core.data_models.integrations.connector.metadata import BuiltConnectorMetadata
    from mp.core.data_models.integrations.custom_families.metadata import BuiltCustomFamily
    from mp.core.data_models.integrations.integration import BuiltIntegration
    from mp.core.data_models.integrations.integration_meta.metadata import BuiltIntegrationMetadata
    from mp.core.data_models.integrations.job.metadata import BuiltJobMetadata
    from mp.core.data_models.integrations.mapping_rules.metadata import BuiltMappingRule


@dataclasses.dataclass(slots=True, frozen=True)
class Metadata(Restructurable):
    out_path: Path
    metadata: BuiltIntegration

    def restructure(self) -> None:
        """Restructure an integration's metadata files to its "out" path."""
        self._restructure_integration_metadata()
        self._restructure_release_notes()
        self._restructure_actions_metadata()
        self._restructure_connectors_metadata()
        self._restructure_job_metadata()
        self._restructure_widget_metadata()
        self._restructure_custom_families()
        self._restructure_mapping_rules()

    def _restructure_integration_metadata(self) -> None:
        metadata: BuiltIntegrationMetadata = self.metadata["metadata"]
        file_content: str = json.dumps(metadata, indent=4, sort_keys=True)
        integration_name: str = metadata["Identifier"]
        file_name: str = mp.core.constants.INTEGRATION_DEF_FILE.format(integration_name)
        metadata_file: Path = self.out_path / file_name
        metadata_file.write_text(file_content, encoding="utf-8")

    def _restructure_release_notes(self) -> None:
        rns: list[BuiltReleaseNote] = sorted(
            self.metadata["release_notes"],
            key=operator.itemgetter("IntroducedInIntegrationVersion"),
        )
        file_content: str = json.dumps(rns, indent=4, sort_keys=True)
        rn_file: Path = self.out_path / mp.core.constants.RN_JSON_FILE
        rn_file.write_text(file_content, encoding="utf-8")

    def _restructure_custom_families(self) -> None:
        meta: Sequence[BuiltCustomFamily] = self.metadata["custom_families"]
        if meta:
            self._restructure_metadata(
                metadata_json={mp.core.constants.OUT_CUSTOM_FAMILIES_FILE: meta},
                dir_name=mp.core.constants.OUT_CUSTOM_FAMILIES_DIR,
                file_suffix="",
            )

    def _restructure_mapping_rules(self) -> None:
        meta: Sequence[BuiltMappingRule] = self.metadata["mapping_rules"]
        if meta:
            self._restructure_metadata(
                metadata_json={mp.core.constants.OUT_MAPPING_RULES_FILE: meta},
                dir_name=mp.core.constants.OUT_MAPPING_RULES_DIR,
                file_suffix="",
            )

    def _restructure_actions_metadata(self) -> None:
        self._restructure_metadata(
            metadata_json=self.metadata["actions"],
            dir_name=mp.core.constants.OUT_ACTIONS_META_DIR,
            file_suffix=mp.core.constants.ACTIONS_META_SUFFIX,
        )

    def _restructure_connectors_metadata(self) -> None:
        self._restructure_metadata(
            metadata_json=self.metadata["connectors"],
            dir_name=mp.core.constants.OUT_CONNECTORS_META_DIR,
            file_suffix=mp.core.constants.CONNECTORS_META_SUFFIX,
        )

    def _restructure_job_metadata(self) -> None:
        self._restructure_metadata(
            metadata_json=self.metadata["jobs"],
            dir_name=mp.core.constants.OUT_JOBS_META_DIR,
            file_suffix=mp.core.constants.JOBS_META_SUFFIX,
        )

    def _restructure_widget_metadata(self) -> None:
        self._restructure_metadata(
            metadata_json=self.metadata["widgets"],
            dir_name=mp.core.constants.OUT_WIDGETS_META_DIR,
            file_suffix=mp.core.constants.JSON_SUFFIX,
        )

    def _restructure_metadata(
        self,
        dir_name: str,
        file_suffix: str,
        metadata_json: (
            Mapping[str, BuiltActionWidgetMetadata]
            | Mapping[str, BuiltJobMetadata]
            | Mapping[str, BuiltConnectorMetadata]
            | Mapping[str, BuiltActionMetadata]
            | Mapping[str, BuiltReleaseNote]
            | Mapping[str, Sequence[BuiltCustomFamily]]
            | Mapping[str, Sequence[BuiltMappingRule]]
        ),
    ) -> None:
        if not metadata_json:
            return

        metadata_path: Path = self.out_path / dir_name
        metadata_path.mkdir(exist_ok=True)
        for name, metadata in metadata_json.items():
            metadata_file: Path = metadata_path / f"{name}{file_suffix}"
            file_content: str = json.dumps(metadata, indent=4, sort_keys=True)
            metadata_file.write_text(file_content, encoding="utf-8")
