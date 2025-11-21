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

import pytest

from mp.core.data_models.playbooks.meta.access_permissions import (
    AccessPermission,
)
from mp.core.data_models.playbooks.meta.metadata import (
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
        with pytest.raises(ValueError):  # noqa: PT011
            AccessPermission.from_built({})

    def test_from_non_built_with_invalid_data_raises_error(self) -> None:
        with pytest.raises(ValueError):  # noqa: PT011
            AccessPermission.from_non_built({})

    def test_from_built_to_built_is_idempotent(self) -> None:
        assert (
            AccessPermission.from_built(BUILT_ACCESS_PERMISSION).to_built()
            == BUILT_ACCESS_PERMISSION
        )

    def test_from_non_built_to_non_built_is_idempotent(self) -> None:
        assert (
            AccessPermission.from_non_built(NON_BUILT_ACCESS_PERMISSION).to_non_built()
            == NON_BUILT_ACCESS_PERMISSION
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
        with pytest.raises(ValueError):  # noqa: PT011
            PlaybookMetadata.from_built("", {})

    def test_from_non_built_with_invalid_data_raises_error(self) -> None:
        with pytest.raises(ValueError):  # noqa: PT011
            PlaybookMetadata.from_non_built("", {})

    def test_from_built_with_none_values(self) -> None:
        assert (
            PlaybookMetadata.from_built("", BUILT_PLAYBOOK_METADATA_WITH_NONE)
            == PLAYBOOK_METADATA_WITH_NONE
        )

    def test_from_non_built_with_none_values(self) -> None:
        assert (
            PlaybookMetadata.from_non_built("", NON_BUILT_PLAYBOOK_METADATA_WITH_NONE)
            == PLAYBOOK_METADATA_WITH_NONE
        )

    def test_to_built_with_none_values(self) -> None:
        assert PLAYBOOK_METADATA_WITH_NONE.to_built() == BUILT_PLAYBOOK_METADATA_WITH_NONE

    def test_to_non_built_with_none_values(self) -> None:
        assert PLAYBOOK_METADATA_WITH_NONE.to_non_built() == NON_BUILT_PLAYBOOK_METADATA_WITH_NONE

    def test_from_built_to_built_is_idempotent(self) -> None:
        assert (
            PlaybookMetadata.from_built("", BUILT_PLAYBOOK_METADATA).to_built()
            == BUILT_PLAYBOOK_METADATA
        )

    def test_from_non_built_to_non_built_is_idempotent(self) -> None:
        assert (
            PlaybookMetadata.from_non_built("", NON_BUILT_PLAYBOOK_METADATA).to_non_built()
            == NON_BUILT_PLAYBOOK_METADATA
        )
