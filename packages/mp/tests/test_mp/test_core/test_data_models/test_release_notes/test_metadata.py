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

from hypothesis import given, settings

from mp.core.data_models.common.release_notes.metadata import (
    BuiltReleaseNote,
    NonBuiltReleaseNote,
    ReleaseNote,
)

from .strategies import (
    ST_VALID_BUILT_RELEASE_NOTE_DICT,
    ST_VALID_NON_BUILT_RELEASE_NOTE_DICT,
)


class TestValidations:
    """
    Tests for pydantic-level model validations.
    """

    @settings(max_examples=30)
    @given(valid_non_built=ST_VALID_NON_BUILT_RELEASE_NOTE_DICT)
    def test_valid_non_built(self, valid_non_built: NonBuiltReleaseNote) -> None:
        ReleaseNote.from_non_built(valid_non_built)

    @settings(max_examples=30)
    @given(valid_built=ST_VALID_BUILT_RELEASE_NOTE_DICT)
    def test_valid_built(self, valid_built: BuiltReleaseNote) -> None:
        ReleaseNote.from_built(valid_built)
