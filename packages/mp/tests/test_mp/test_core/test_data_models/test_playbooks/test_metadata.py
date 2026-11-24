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

from typing import cast

import pytest

from mp.core.data_models.playbooks.meta.access_permissions import (
    AccessPermission,
    BuiltAccessPermission,
    NonBuiltAccessPermission,
)
from mp.core.data_models.playbooks.meta.metadata import (
    BuiltPlaybookMetadata,
    NonBuiltPlaybookMetadata,
    PlaybookExecutionScope,
    PlaybookMetadata,
)

from .constants import (
    ACCESS_PERMISSION,
    BUILT_ACCESS_PERMISSION,
    BUILT_PLAYBOOK_METADATA,
    BUILT_PLAYBOOK_METADATA_WITH_NONE,
    NON_BUILT_ACCESS_PERMISSION,
    NON_BUILT_PLAYBOOK_METADATA,
    NON_BUILT_PLAYBOOK_METADATA_WITH_NONE,
    PLAYBOOK_METADATA,
    PLAYBOOK_METADATA_WITH_NONE,
)


class TestAccessPermissionDataModel:
    def test_from_built_with_valid_data(self) -> None:
        assert AccessPermission.from_built(BUILT_ACCESS_PERMISSION) == ACCESS_PERMISSION

    def test_from_non_built_with_valid_data(self) -> None:
        assert AccessPermission.from_non_built(NON_BUILT_ACCESS_PERMISSION) == ACCESS_PERMISSION

    def test_to_built(self) -> None:
        assert ACCESS_PERMISSION.to_built() == BUILT_ACCESS_PERMISSION

    def test_to_non_built(self) -> None:
        assert ACCESS_PERMISSION.to_non_built() == NON_BUILT_ACCESS_PERMISSION

    def test_from_built_with_invalid_data_raises_error(self) -> None:
        with pytest.raises(ValueError):  # ruff:ignore[pytest-raises-too-broad]
            AccessPermission.from_built(cast("BuiltAccessPermission", cast("object", {})))

    def test_from_non_built_with_invalid_data_raises_error(self) -> None:
        with pytest.raises(ValueError):  # ruff:ignore[pytest-raises-too-broad]
            AccessPermission.from_non_built(cast("NonBuiltAccessPermission", cast("object", {})))

    def test_from_built_to_built_is_idempotent(self) -> None:
        assert AccessPermission.from_built(BUILT_ACCESS_PERMISSION).to_built() == BUILT_ACCESS_PERMISSION

    def test_from_non_built_to_non_built_is_idempotent(self) -> None:
        assert (
            AccessPermission.from_non_built(NON_BUILT_ACCESS_PERMISSION).to_non_built() == NON_BUILT_ACCESS_PERMISSION
        )


class TestPlaybookMetadataDataModel:
    def test_from_built_with_valid_data(self) -> None:
        assert PlaybookMetadata.from_built("", BUILT_PLAYBOOK_METADATA) == PLAYBOOK_METADATA

    def test_from_non_built_with_valid_data(self) -> None:
        assert PlaybookMetadata.from_non_built("", NON_BUILT_PLAYBOOK_METADATA) == PLAYBOOK_METADATA

    def test_to_built(self) -> None:
        assert PLAYBOOK_METADATA.to_built() == BUILT_PLAYBOOK_METADATA

    def test_to_non_built(self) -> None:
        assert PLAYBOOK_METADATA.to_non_built() == NON_BUILT_PLAYBOOK_METADATA

    def test_from_built_with_invalid_data_raises_error(self) -> None:
        with pytest.raises(ValueError):  # ruff:ignore[pytest-raises-too-broad]
            PlaybookMetadata.from_built("", {})

    def test_from_non_built_with_invalid_data_raises_error(self) -> None:
        with pytest.raises(ValueError):  # ruff:ignore[pytest-raises-too-broad]
            PlaybookMetadata.from_non_built("", {})

    def test_from_built_with_none_values(self) -> None:
        assert PlaybookMetadata.from_built("", BUILT_PLAYBOOK_METADATA_WITH_NONE) == PLAYBOOK_METADATA_WITH_NONE

    def test_from_non_built_with_none_values(self) -> None:
        assert PlaybookMetadata.from_non_built("", NON_BUILT_PLAYBOOK_METADATA_WITH_NONE) == PLAYBOOK_METADATA_WITH_NONE

    def test_to_built_with_none_values(self) -> None:
        assert PLAYBOOK_METADATA_WITH_NONE.to_built() == BUILT_PLAYBOOK_METADATA_WITH_NONE

    def test_to_non_built_with_none_values(self) -> None:
        assert PLAYBOOK_METADATA_WITH_NONE.to_non_built() == NON_BUILT_PLAYBOOK_METADATA_WITH_NONE

    def test_from_built_to_built_is_idempotent(self) -> None:
        assert PlaybookMetadata.from_built("", BUILT_PLAYBOOK_METADATA).to_built() == BUILT_PLAYBOOK_METADATA

    def test_from_non_built_to_non_built_is_idempotent(self) -> None:
        assert (
            PlaybookMetadata.from_non_built("", NON_BUILT_PLAYBOOK_METADATA).to_non_built()
            == NON_BUILT_PLAYBOOK_METADATA
        )

    def test_case_playbook_execution_scope_round_trip(self) -> None:
        built_case_meta: BuiltPlaybookMetadata = {
            **BUILT_PLAYBOOK_METADATA,
            "ExecutionScope": 2,
        }
        meta: PlaybookMetadata = PlaybookMetadata.from_built("", built_case_meta)
        assert meta.execution_scope == PlaybookExecutionScope.CASE
        assert meta.to_built() == built_case_meta

        non_built_case_meta: NonBuiltPlaybookMetadata = meta.to_non_built()
        assert non_built_case_meta["execution_scope"] == "case"
        assert PlaybookMetadata.from_non_built("", non_built_case_meta).to_built() == built_case_meta

    def test_execution_scope_string_variants_from_built(self) -> None:
        for raw_val, expected in [
            ("CASE", PlaybookExecutionScope.CASE),
            ("2", PlaybookExecutionScope.CASE),
            ("ALERT", PlaybookExecutionScope.ALERT),
            ("EXECUTION_SCOPE_UNSPECIFIED", PlaybookExecutionScope.UNSPECIFIED),
        ]:
            built_meta: BuiltPlaybookMetadata = {
                **BUILT_PLAYBOOK_METADATA,
                "ExecutionScope": raw_val,
            }
            meta: PlaybookMetadata = PlaybookMetadata.from_built("", built_meta)
            assert meta.execution_scope == expected

    def test_execution_scope_boolean_raises_value_error(self) -> None:
        for invalid_bool in (True, False):
            built_meta: BuiltPlaybookMetadata = {
                **BUILT_PLAYBOOK_METADATA,
                "ExecutionScope": invalid_bool,
            }
            with pytest.raises(ValueError, match="Failed to load built"):
                PlaybookMetadata.from_built("", built_meta)
