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

import datetime
import uuid
from typing import TYPE_CHECKING

import pytest
from soar_sdk import SiemplifyUtils
from TIPCommon.cache import Cache, _dump_property_value, _row_is_too_long

from integration_testing.set_meta import set_metadata

from .conftest import (
    action_cache,
    connector_cache,
    job_cache,
)

if TYPE_CHECKING:
    from collections.abc import Callable


class TestContext:
    @pytest.mark.parametrize("cache_class", [action_cache, connector_cache, job_cache])
    @set_metadata
    def test_action_cache_without_maxsize(
        self,
        cache_class: Callable[[int | None], Cache],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(SiemplifyUtils, "MAXIMUM_PROPERTY_VALUE", 10_000)
        cache: Cache = cache_class(None)
        rows_asserted = 0

        while not _row_is_too_long(_dump_property_value(cache.content)):
            cache[str(uuid.uuid4())] = datetime.datetime.now(
                tz=datetime.UTC,
            ).timestamp()
            rows_asserted += 1

        cache.commit()
        expected_cache_chunks: int = 2
        assert len(cache._cache_chunks) == expected_cache_chunks  # noqa: SLF001
        assert len(cache) == rows_asserted

        del cache
        cache = cache_class(None)
        assert len(cache) == rows_asserted

    @pytest.mark.parametrize(
        ("cache_class", "rows_to_assert", "max_size"),
        [
            (action_cache, 100, 200),
            (action_cache, 200, 200),
            (action_cache, 300, 200),
            (action_cache, 500, 450),
            (action_cache, 1_000, 500),
            (job_cache, 12_000, 10_000),
            (job_cache, 3_000, 10_000),
            (job_cache, 20_000, 10_000),
            (connector_cache, 12_000, 10_000),
            (connector_cache, 3_000, 10_000),
            (connector_cache, 20_000, 10_000),
        ],
    )
    @set_metadata
    def test_action_cache_with_maxsize(
        self,
        cache_class: Callable[[int | None], Cache],
        monkeypatch: pytest.MonkeyPatch,
        rows_to_assert: int,
        max_size: int,
    ) -> None:
        """Test different caches with different sizes and number of elements.

        Steps:
            1. Patch MAXIMUM_PROPERTY_VALUE to be 10_000 (for convenience)
            2. Create empty cache class
            3. Populate it with values
            4. Assert that cache is within expected size
            5. Assert that the latest value are in the cache if number of elements
                exceeds cache size
        """
        monkeypatch.setattr(SiemplifyUtils, "MAXIMUM_PROPERTY_VALUE", 10_000)
        error_threshold = 0.1
        cache: Cache = cache_class(max_size)

        asserted_keys = []
        for _ in range(rows_to_assert):
            key = str(uuid.uuid4())
            cache[key] = datetime.datetime.now(tz=datetime.UTC).timestamp()
            asserted_keys.append(key)

        cache.commit()
        expected_size = min(rows_to_assert, max_size)
        assert len(cache) >= expected_size
        assert len(cache) <= max_size
        assert (
            len(set(asserted_keys[-expected_size // 2 :]).difference(cache))
            < max_size * error_threshold
        )

        del cache
        cache = cache_class(max_size)
        assert len(cache) >= expected_size
        assert len(cache) <= max_size
