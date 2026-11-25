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

from unittest.mock import Mock

from typing import Any, Callable, ContextManager

import arrow

from sentinel_one_v2.core.utils import read_ids


NUM_OF_MILLI_IN_SEC = 1_000


# pylint: disable=redefined-outer-name


class TestUtils:
    def test_read_ids_file_not_exist(self) -> None:
        assert read_ids("./", Mock()) == {}

    def test_read_ids_id_timestamp_passed(
        self,
        temp_json_file: Callable[[dict[str, Any]], ContextManager],
    ) -> None:
        one_day_ago = (
            arrow.utcnow().shift(hours=-24).int_timestamp * NUM_OF_MILLI_IN_SEC
        )
        ids = {"one-day-ago": one_day_ago}

        with temp_json_file(ids) as temp_file:
            result = read_ids(
                run_folder="./",
                logger=Mock(),
                ids_file_name=temp_file.name,
                max_hours_backwards=10,
            )
            assert result == {}

    def test_read_ids_id_timestamp_future(
        self,
        temp_json_file: Callable[[dict[str, Any]], ContextManager],
    ) -> None:
        one_hour_from_now = (
            arrow.utcnow().shift(hours=1).int_timestamp * NUM_OF_MILLI_IN_SEC
        )
        ids = {"id-one-hour-from-now": one_hour_from_now}

        with temp_json_file(ids) as temp_file:
            result = read_ids(
                run_folder="./",
                logger=Mock(),
                ids_file_name=temp_file.name,
                max_hours_backwards=10,
            )
            assert result == ids
