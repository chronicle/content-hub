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

import unittest.mock

import pytest
from google.cloud.exceptions import GoogleCloudError

from google_big_query.core.GoogleBigQueryManager import (
    GoogleBigQueryApiManager,
    GoogleBigQueryExceptions,
)


def test_init() -> None:
    manager: GoogleBigQueryApiManager = GoogleBigQueryApiManager("proj", None)

    assert manager is not None


class TestTestConnectivity:

    def test_test_connectivity_raises_manager_error_when_fail(self) -> None:
        manager: GoogleBigQueryApiManager = GoogleBigQueryApiManager("proj", None)
        with pytest.raises(
            GoogleBigQueryExceptions.GoogleBigQueryManagerError
        ), unittest.mock.patch.object(
            manager, "list_datasets", side_effect=GoogleCloudError("")
        ):
            manager.test_connectivity()
