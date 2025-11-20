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

from mp.core.data_models.playbooks.trigger.metadata import (
    Trigger,
)

from .constants import (
    BUILT_TRIGGER,
    BUILT_TRIGGER_WITH_NONE,
    NON_BUILT_TRIGGER,
    NON_BUILT_TRIGGER_WITH_NONE,
    TRIGGER,
    TRIGGER_WITH_NONE,
)


class TestTriggerDataModel:
    def test_from_built_with_valid_data(self) -> None:
        assert Trigger.from_built(BUILT_TRIGGER) == TRIGGER

    def test_from_non_built_with_valid_data(self) -> None:
        assert Trigger.from_non_built(NON_BUILT_TRIGGER) == TRIGGER

    def test_to_built(self) -> None:
        assert TRIGGER.to_built() == BUILT_TRIGGER

    def test_to_non_built(self) -> None:
        assert TRIGGER.to_non_built() == NON_BUILT_TRIGGER

    def test_from_built_with_invalid_data_raises_error(self) -> None:
        with pytest.raises(ValueError):  # noqa: PT011
            Trigger.from_built({})

    def test_from_non_built_with_invalid_data_raises_error(self) -> None:
        with pytest.raises(ValueError):  # noqa: PT011
            Trigger.from_non_built({})

    def test_from_built_with_none_values(self) -> None:
        assert Trigger.from_built(BUILT_TRIGGER_WITH_NONE) == TRIGGER_WITH_NONE

    def test_from_non_built_with_none_values(self) -> None:
        assert Trigger.from_non_built(NON_BUILT_TRIGGER_WITH_NONE) == TRIGGER_WITH_NONE

    def test_to_built_with_none_values(self) -> None:
        assert TRIGGER_WITH_NONE.to_built() == BUILT_TRIGGER_WITH_NONE

    def test_to_non_built_with_none_values(self) -> None:
        assert TRIGGER_WITH_NONE.to_non_built() == NON_BUILT_TRIGGER_WITH_NONE

    def test_from_built_to_built_is_idempotent(self) -> None:
        assert Trigger.from_built(BUILT_TRIGGER).to_built() == BUILT_TRIGGER

    def test_from_non_built_to_non_built_is_idempotent(self) -> None:
        assert Trigger.from_non_built(NON_BUILT_TRIGGER).to_non_built() == NON_BUILT_TRIGGER
