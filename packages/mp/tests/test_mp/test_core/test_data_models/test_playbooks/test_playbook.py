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

from pathlib import Path

from mp.core.data_models.playbooks.meta.metadata import PlaybookExecutionScope
from mp.core.data_models.playbooks.playbook import BuiltPlaybook, Playbook

MOCK_BUILT_PLAYBOOK_PATH: Path = Path("mock_built_playbook/mock_built_playbook.json")
MOCK_NON_BUILT_PLAYBOOK_PATH: Path = Path("third_party/community/mock_non_built_playbook")


class TestPlaybookDataModel:
    def test_load_non_built_from_path(self, mock_playbook_path: Path) -> None:
        pa: Path = mock_playbook_path / MOCK_NON_BUILT_PLAYBOOK_PATH
        Playbook.from_non_built_path(pa)

    def test_convert_non_built_to_built(self, mock_playbook_path: Path) -> None:
        pa: Path = mock_playbook_path / MOCK_NON_BUILT_PLAYBOOK_PATH
        Playbook.from_non_built_path(pa).to_built()

    def test_convert_non_built_to_non_built(self, mock_playbook_path: Path) -> None:
        pa: Path = mock_playbook_path / MOCK_NON_BUILT_PLAYBOOK_PATH
        Playbook.from_non_built_path(pa).to_non_built()

    def test_load_built_from_path(self, mock_playbook_path: Path) -> None:
        pa: Path = mock_playbook_path / MOCK_BUILT_PLAYBOOK_PATH
        Playbook.from_built_path(pa)

    def test_convert_built_to_built(self, mock_playbook_path: Path) -> None:
        pa: Path = mock_playbook_path / MOCK_BUILT_PLAYBOOK_PATH
        Playbook.from_built_path(pa).to_built()

    def test_convert_built_to_non_built(self, mock_playbook_path: Path) -> None:
        pa: Path = mock_playbook_path / MOCK_BUILT_PLAYBOOK_PATH
        Playbook.from_built_path(pa).to_non_built()

    def test_case_playbook_preserves_execution_scope(self, mock_playbook_path: Path) -> None:
        pa: Path = mock_playbook_path / MOCK_NON_BUILT_PLAYBOOK_PATH
        pb: Playbook = Playbook.from_non_built_path(pa)
        assert "ExecutionScope" not in pb.to_built()["Definition"]

        pb.meta_data.execution_scope = PlaybookExecutionScope.CASE
        built: BuiltPlaybook = pb.to_built()
        assert built["Definition"]["ExecutionScope"] == 2
        assert pb.to_non_built()["meta_data"]["execution_scope"] == "case"
