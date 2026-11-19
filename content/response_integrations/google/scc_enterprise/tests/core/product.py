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

from TIPCommon.types import SingleJson


@dataclasses.dataclass
class GoogleSecurityCommandCenter(abc.ABC):
    configs: dict[str, SingleJson] = dataclasses.field(default_factory=dict)
    findings: dict[str, SingleJson] = dataclasses.field(default_factory=dict)
    sources: dict[str, SingleJson] = dataclasses.field(default_factory=dict)

    def add_source(self, source_json: SingleJson):
        self.sources[source_json["name"]] = source_json

    def list_sources(self) -> list[SingleJson]:
        return list(self.sources.values())

    def add_finding(self, finding_json: SingleJson):
        self.findings[finding_json["finding"]["name"]] = finding_json

    def list_findings(self, finding_names: list[str] = None) -> list[SingleJson]:
        if finding_names is None:
            return list(self.findings.values())

        return [self.findings[_name] for _name in finding_names]

    def add_notifications_config(
            self,
            config_name: str,
            config_json: SingleJson
    ) -> None:
        """Add notifications config."""
        self.configs[config_name] = config_json

    def remove_notifications_config(self, config_name: str) -> None:
        del self.configs[config_name]

    def get_notifications_config(self, config_name: str) -> SingleJson | None:
        return self.configs.get(config_name)

    def update_notifications_config(
            self,
            config_name: str,
            config_json: SingleJson
    ) -> SingleJson | None:
        """Update notifications config."""
        if config_name not in self.configs:
            return None

        self.configs[config_name].update(config_json)
        return self.configs[config_name]
