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
from mp.core.data_models.playbooks.playbook_widget.metadata import (
    PlaybookWidgetMetadata,
)
from .constants import (
    BUILT_PLAYBOOK_WIDGET_METADATA,
    PLAYBOOK_WIDGET_METADATA,
    NON_BUILT_PLAYBOOK_WIDGET_METADATA,
    BUILT_PLAYBOOK_WIDGET_METADATA_WITH_NONE,
    PLAYBOOK_WIDGET_METADATA_WITH_NONE,
    NON_BUILT_PLAYBOOK_WIDGET_METADATA_WITH_NONE,
)


class TestPlaybookWidgetMetadataDataModel:
    def test_from_built_with_valid_data(self):
        assert PlaybookWidgetMetadata._from_built("", BUILT_PLAYBOOK_WIDGET_METADATA) == PLAYBOOK_WIDGET_METADATA

    def test_from_non_built_with_valid_data(self):
        assert PlaybookWidgetMetadata._from_non_built("", NON_BUILT_PLAYBOOK_WIDGET_METADATA) == PLAYBOOK_WIDGET_METADATA

    def test_to_built(self):
        assert PLAYBOOK_WIDGET_METADATA.to_built() == BUILT_PLAYBOOK_WIDGET_METADATA

    def test_to_non_built(self):
        assert PLAYBOOK_WIDGET_METADATA.to_non_built() == NON_BUILT_PLAYBOOK_WIDGET_METADATA

    def test_from_built_with_invalid_data_raises_error(self):
        with pytest.raises(ValueError):
            PlaybookWidgetMetadata.from_built("", {})

    def test_from_non_built_with_invalid_data_raises_error(self):
        with pytest.raises(ValueError):
            PlaybookWidgetMetadata.from_non_built("", {})

    def test_from_built_with_none_values(self):
        assert PlaybookWidgetMetadata._from_built("", BUILT_PLAYBOOK_WIDGET_METADATA_WITH_NONE) == PLAYBOOK_WIDGET_METADATA_WITH_NONE

    def test_from_non_built_with_none_values(self):
        assert PlaybookWidgetMetadata._from_non_built("", NON_BUILT_PLAYBOOK_WIDGET_METADATA_WITH_NONE) == PLAYBOOK_WIDGET_METADATA_WITH_NONE

    def test_to_built_with_none_values(self):
        assert PLAYBOOK_WIDGET_METADATA_WITH_NONE.to_built() == BUILT_PLAYBOOK_WIDGET_METADATA_WITH_NONE

    def test_to_non_built_with_none_values(self):
        assert PLAYBOOK_WIDGET_METADATA_WITH_NONE.to_non_built() == NON_BUILT_PLAYBOOK_WIDGET_METADATA_WITH_NONE

    def test_from_built_to_built_is_idempotent(self):
        assert PlaybookWidgetMetadata._from_built("", BUILT_PLAYBOOK_WIDGET_METADATA).to_built() == BUILT_PLAYBOOK_WIDGET_METADATA

    def test_from_non_built_to_non_built_is_idempotent(self):
        assert PlaybookWidgetMetadata._from_non_built("", NON_BUILT_PLAYBOOK_WIDGET_METADATA).to_non_built() == NON_BUILT_PLAYBOOK_WIDGET_METADATA
